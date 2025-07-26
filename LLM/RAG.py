from uuid import uuid4

import pandas as pd
from langchain.embeddings.base import Embeddings
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.vectorstores import Qdrant
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer

from LLM.Environment import Environment


class JinaEmbeddings(Embeddings):
    def __init__(self, task="retrieval.passage"):
        print("Creating Jina Embeddings instance...")
        self.model = SentenceTransformer(
            "jinaai/jina-embeddings-v3", trust_remote_code=True
        )
        print("Jina Embeddings instance created.")
        self.task = task

    def embed_documents(self, texts):
        return self.model.encode(texts, task=self.task, prompt_name=self.task)

    def embed_query(self, text):
        return self.model.encode(
            [text], task="retrieval.query", prompt_name="retrieval.query"
        )[0]


class QdrantClientWrapper:
    def __init__(self, env: Environment):
        self.qdrant_client = QdrantClient(
            url=env.get_qdrant_url(), api_key=env.get_qdrant_api_key()
        )
        self.general_collection_name = env.get_general_collection_name()
        self.function_calling_collection_name = (
            env.get_function_calling_collection_name()
        )
        self.QA_collection_name = env.get_QA_collection_name()


class RAG:
    def __init__(
        self,
        env: Environment,
    ):
        self.qdrant_client_wrapper = QdrantClientWrapper(env)
        self.qdrant_client = self.qdrant_client_wrapper.qdrant_client

        self.general_collection_name = (
            self.qdrant_client_wrapper.general_collection_name
        )
        self.QA_collection_name = self.qdrant_client_wrapper.QA_collection_name
        self.function_calling_collection_name = (
            self.qdrant_client_wrapper.function_calling_collection_name
        )
        self.embedding = JinaEmbeddings()
        self.k = 20

        self.qdrant = Qdrant(
            client=self.qdrant_client,
            collection_name=self.general_collection_name,
            embeddings=self.embedding,
            content_payload_key="text",
        )
        # Reranker (from RerankerNoGroq notebook)
        print("Creating CrossEncoder model...")
        self.model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.model, top_n=15)

    def get_documents(self, question: str, previous_points: list[str]):
        query_embedding = self.embedding.embed_query(question)
        (general_results, general_point_ids) = self.get_documents_helper(
            query_embedding,
            question,
            self.general_collection_name,
            min_score=0.4,
            max_returns=10,
        )

        (function_calling_results, function_calling_point_ids) = (
            self.get_documents_helper(
                query_embedding,
                question,
                self.function_calling_collection_name,
                min_score=0.4,
                max_returns=1,
                previous_points=previous_points,
            )
        )
        all_results = general_results._append(function_calling_results)
        return (all_results, function_calling_point_ids)

    def get_documents_helper(
        self,
        query_embedding,
        question: str,
        collection_name: str,
        min_score: float = 0.4,
        max_returns: int = 1,
        previous_points: list[str] = [],
    ):
        search_results = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=self.k,  # same as k in retriever
            with_payload=True,
            with_vectors=False,
        )
        search_results = [hit for hit in search_results if hit.score >= min_score]

        documents = [
            Document(
                page_content=hit.payload["text"],
                metadata={
                    "score": hit.score,
                    "source": hit.payload.get("source", "unknown"),
                    "point_id": hit.id,
                },
            )
            for hit in search_results
        ]

        # No documents were above threshold
        if documents == []:
            if previous_points:
                previous_point_search = self.qdrant_client.retrieve(
                    collection_name=collection_name,
                    ids=previous_points,
                    with_payload=True,
                )
                # Get only most recent result from previous data points
                prev_df = pd.DataFrame(
                    [
                        {
                            "contents": previous_point_search[0].payload["text"],
                            "sources": previous_point_search[0].payload.get(
                                "source", "unknown"
                            ),
                            "point_ids": previous_point_search[0].id,
                        }
                    ]
                )
                return (prev_df, prev_df["point_ids"])
            return (pd.DataFrame({"contents": []}), [])

        # Rerank using the CrossEncoderReranker
        reranked_documents = self.compressor.compress_documents(
            documents, query=question
        )

        # Ensure there is only a maximum of around 2000 tokens of data
        max_tokens = 2000
        total_tokens = 0
        selected_docs = []

        for doc in reranked_documents:
            approx_tokens = len(doc.page_content) // 4
            if total_tokens + approx_tokens > max_tokens:
                break
            selected_docs.append(doc)
            total_tokens += approx_tokens

        compression_contents = [doc.page_content for doc in selected_docs]
        sources = [doc.metadata.get("source", "unknown") for doc in selected_docs]
        point_ids = [doc.metadata.get("point_id", "unknown") for doc in selected_docs]
        df = pd.DataFrame(
            {
                "contents": compression_contents,
                "sources": sources,
                "point_ids": point_ids,
            }
        )
        df = df[:max_returns]

        return (df, df["point_ids"])

    # Retrieve Q&A pairs for feedback loop
    def get_qa_docs(self, question: str):
        search_results = self.qdrant_client.search(
            collection_name=self.QA_collection_name,
            query_vector=self.embedding.embed_query(question),
            limit=5,
            with_payload=True,
            with_vectors=False,
        )

        qa_docs = []
        for hit in search_results:
            qa_docs.append(
                Document(
                    page_content=hit.payload["text"], metadata={"score": hit.score}
                )
            )

        df_qa = pd.DataFrame({"contents": qa_docs})
        return df_qa

    # Uploads new Q&A pair to Qdrant Q&A collection
    # When we receive a "thumbs-up" feedback on an LLM response, backend-api/src/LLM/service.py calls this function
    async def upload_new_qa(self, qa_pair: dict):
        current_qa_id = uuid4().hex

        # Determine the actual text content for embedding and payload
        actual_text_content = qa_pair["text"]
        if isinstance(actual_text_content, dict) and "response" in actual_text_content:
            actual_text_content = actual_text_content["response"]
        elif not isinstance(actual_text_content, str):
            actual_text_content = str(actual_text_content)

        QA_text = (
            f"Question: {qa_pair['original_question']} Answer: {actual_text_content}"
        )

        # embedding_vector = self.Qdrant_model.encode(QA_text)
        embedding_vector = self.embedding.embed_documents([QA_text])[0]

        item_payload = {
            "text": actual_text_content,
            "original_question": qa_pair["original_question"],
        }

        # Create a PointStruct for the new data point
        new_point = PointStruct(
            id=current_qa_id, vector=embedding_vector, payload=item_payload
        )
        # Upload the new point to Qdrant collection
        self.qdrant_client.upsert(
            collection_name=self.QA_collection_name,
            points=[new_point],  # upsert expects a list of points
        )
