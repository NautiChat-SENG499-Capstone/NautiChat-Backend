from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.documents import Document
from qdrant_client.http.models import VectorParams, Distance
import pandas as pd
from Environment import Environment


class JinaEmbeddings(Embeddings):
    def __init__(self, task="retrieval.passage"):
        print("Creating Jina Embeddings instance...")
        self.model = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)
        print("Jina Embeddings instance created.")
        self.task = task

    def embed_documents(self, texts):
        return self.model.encode(texts, task=self.task, prompt_name=self.task)

    def embed_query(self, text):
        return self.model.encode([text], task="retrieval.query", prompt_name="retrieval.query")[0]


class QdrantClientWrapper:
    def __init__(self, env: Environment):
        self.qdrant_client = QdrantClient(url=env.get_qdrant_url(), api_key=env.get_qdrant_api_key())
        self.collection_name = env.get_collection_name()


class RAG:
    def __init__(self, env: Environment):
        self.qdrant_client_wrapper = QdrantClientWrapper(env)
        self.qdrant_client = self.qdrant_client_wrapper.qdrant_client
        self.collection_name = self.qdrant_client_wrapper.collection_name
        print("Creating Jina Embeddings instance...")
        self.embedding = JinaEmbeddings()
        print("Creating Qdrant instance...")
        self.qdrant = Qdrant(
            client=self.qdrant_client,
            collection_name=env.get_collection_name(),
            embeddings=self.embedding,
            content_payload_key="text",
        )
        # Qdrant Retriever
        print("Creating Qdrant retriever...")
        self.retriever = self.qdrant.as_retriever(search_kwargs={"k": 100})
        # Reranker (from RerankerNoGroq notebook)
        print("Creating CrossEncoder model...")
        self.model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.model, top_n=15)

    def get_documents(self, question: str):
    
        query_embedding = self.embedding.embed_query(question)
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=100,  # same as k in retriever
            with_payload=True,
            with_vectors=False
        )

        # Filter results by score threshold
        filtered_hits = [hit for hit in search_results if hit.score >= 0.4]

        documents = [
            Document(
                page_content=hit.payload["text"],
                metadata={"score": hit.score}
            )
            for hit in filtered_hits
        ]        

        # No documents were above threshold
        if documents == []:
            return pd.DataFrame({"contents": []})

        # Rerank using the CrossEncoderReranker
        reranked_documents = self.compressor.compress_documents(documents, query=question)

        #Ensure there is only a maximum of around 2000 tokens of data
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
        df = pd.DataFrame({"contents": compression_contents})
        return df
