import pandas as pd
from langchain.embeddings.base import Embeddings
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.vectorstores import Qdrant
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.http.models import VectorParams, Distance, FieldCondition, Filter, MatchValue, PointStruct

from uuid import uuid4

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
        self.collection_name = env.get_collection_name()
        self.QA_collection_name = env.get_QA_collection_name()


class RAG:
    def __init__(
        self,
        env: Environment,
        *,
        embedder: Embeddings | None = None,
        qdrant_client: QdrantClient | None = None,
    ):
        self.qdrant_client_wrapper = QdrantClientWrapper(env)
        self.qdrant_client = qdrant_client or self.qdrant_client_wrapper.qdrant_client
        self.collection_name = self.qdrant_client_wrapper.collection_name
        self.QA_collection_name = self.qdrant_client_wrapper.QA_collection_name
        self.embedding = embedder or JinaEmbeddings()

        # self.qdrant = Qdrant(
        #     client=self.qdrant_client,
        #     collection_name=self.collection_name,
        #     embeddings=self.embedding,
        #     content_payload_key="text",
        # )

        self.qdrant_ONC = Qdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.embedding,
            content_payload_key="text",
        )
        self.qdrant_QA = Qdrant(
            client=self.qdrant_client,
            collection_name=self.QA_collection_name,
            embeddings=self.embedding,
            content_payload_key="text",
        )

        self.filters = {
            "positive_feedback": Filter(
                must=[
                    FieldCondition(
                        key="feedback",
                        match=MatchValue(value="positive"),
                    )
                ]
            ),
            "no_filter": None # Add this for cases where no specific filter is needed
        }
        # Qdrant Retriever
        print("Creating Qdrant retriever...")
        # self.retriever = self.qdrant.as_retriever(search_kwargs={"k": 100})
        print(f"Creating Qdrant retriever for {self.collection_name}...")
        self.retriever_ONC = self.qdrant_ONC.as_retriever(
            search_kwargs={"k": 100, "filter": self.filters["no_filter"]} # Default to positive feedback
        )

        # Qdrant Retriever for the no-filter collection
        print(f"Creating Qdrant retriever for {self.QA_collection_name}...")
        self.retriever_QA = self.qdrant_QA.as_retriever(
            search_kwargs={"k": 100, "filter": self.filters["positive_feedback"]} # No filter applied
        )

        # Reranker (from RerankerNoGroq notebook)
        print("Creating CrossEncoder model...")
        self.model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.model, top_n=15)

        self.Qdrant_model = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)

    def get_documents(self, question: str) -> tuple[pd.DataFrame, list[str]]: 
        
        query_embedding = self.embedding.embed_query(question)

        #Searching through ONC-Knowledge collection
        ONC_search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=100,  # same as k in retriever
            with_payload=True,
            with_vectors=False,
        )
        #Searching through Q&A collection
        QA_search_results = self.qdrant_client.search(
            collection_name=self.QA_collection_name,
            query_vector=query_embedding,
            limit=100, 
            with_payload=True,
            with_vectors=False,
            query_filter=self.filters["positive_feedback"] # Only pull positively rated documents
        )

        filtered_qa_hits = [hit for hit in QA_search_results if hit.score >= 0.4]

        qa_docs = []
        # contributing_qa_ids = [] # <-- New list to store QA IDs from this collection
        for hit in filtered_qa_hits:
            qa_id = hit.payload.get("qa_id")
            # if qa_id: # Only add if qa_id exists
                # contributing_qa_ids.append(qa_id)
            qa_docs.append(
                Document(
                    page_content=hit.payload["text"],
                    metadata={"score": hit.score, "source_collection": self.QA_collection_name, "qa_id": qa_id}
                )
            )

        # Filter results by score threshold
        filtered_hits = [hit for hit in ONC_search_results if hit.score >= 0.4]

        documents = [
            Document(
                page_content=hit.payload["text"],
                metadata={"score": hit.score}
            )
            for hit in filtered_hits
        ]        

        
        # No documents were above threshold
        if not documents and not qa_docs: # Check both lists
            return pd.DataFrame({"contents": []}), [], pd.DataFrame({"contents": []}) # Return empty dfs and empty list of qa_ids
        # Rerank using the CrossEncoderReranker
        reranked_documents = self.compressor.compress_documents(documents, query=question)

        #Ensure there is only a maximum of around 2000 tokens of data
        max_tokens = 2000
        total_tokens = 0
        selected_docs = []

        # combined_final_documents = qa_documents + reranked_documents
        combined_final_documents = reranked_documents

        for doc in combined_final_documents:
            approx_tokens = len(doc.page_content) // 4
            if total_tokens + approx_tokens > max_tokens:
                break
            selected_docs.append(doc)
            total_tokens += approx_tokens
        
        #Printing out docs for me to debug
        for i, doc in enumerate(qa_docs):
                print(f"-- Document {i+1} --")
                print(f"Page Content: {doc.page_content}")
                if hasattr(doc, 'metadata'):
                    print(f"Metadata: {doc.metadata}")
                    # Get qa_id and print
                    qa_id = doc.metadata.get("qa_id", "N/A")
                    print(f"QA ID: {qa_id}") # This line will print the QA ID

                print("-" * 20)

        compression_contents = [doc.page_content for doc in selected_docs]

        df_onc = pd.DataFrame({"contents": compression_contents})
        df_qa = pd.DataFrame({"contents": qa_docs}) # DataFrame for QA styling content
        return df_onc, df_qa
    
    #Upload new Q&A pair to Qdrant Q&A collection
    async def upload_new_qa(self, qa_pair: dict):
        current_qa_id = uuid4().hex

    #     qa_pair = {
    #     "original_question": user_input,
    #     "text": {"response": llm_response}
    # }
        # Determine the actual text content for embedding and payload
        actual_text_content = qa_pair["text"]
        if isinstance(actual_text_content, dict) and "response" in actual_text_content:
            actual_text_content = actual_text_content["response"]
        elif not isinstance(actual_text_content, str):

            actual_text_content = str(actual_text_content)

        QA_text = f"Question: {qa_pair['original_question']} Answer: {actual_text_content}"

        embedding_vector = self.Qdrant_model.encode(QA_text)

        item_payload = {
            # FIX 1: Corrected: Directly use actual_text_content
            "text": actual_text_content,
            "original_question": qa_pair["original_question"],
            # FIX 3: Important for feedback loop, should NOT be removed
            "qa_id": current_qa_id,
            "feedback": "positive"   # Initial feedback state
        }
        
        # Create a PointStruct for the new data point
        new_point = PointStruct(
            id=current_qa_id,
            vector=embedding_vector,
            payload=item_payload
        )

        # Upload the new point to Qdrant collection
        # Using upsert is suitable for adding a single point.
        self.qdrant_client.upsert(
            collection_name=self.QA_collection_name,
            points=[new_point]  # upsert expects a list of points
        )
        print(f"Uploaded new QA pair with ID: {current_qa_id}")
    
    def update_qa_feedback(self, qa_id: str, new_feedback: str):
        """
        Updates the feedback for a specific Q&A document in the Q&A collection.
        """
        # Find the point by qa_id
        search_result = self.qdrant_client.scroll(
            collection_name=self.QA_collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="qa_id",
                        match=MatchValue(value=qa_id)
                    )
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False
        )

        if search_result and search_result[0]:
            point_id = search_result[0][0].id
            # Update the payload
            self.qdrant_client.set_payload(
                collection_name=self.QA_collection_name,
                payload={"feedback": new_feedback},
                points=[point_id]
            )
            print(f"Updated feedback for QA ID {qa_id} to {new_feedback}")
        else:
            print(f"QA ID {qa_id} not found in collection {self.QA_collection_name}")