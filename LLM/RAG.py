from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from qdrant_client.http.models import VectorParams, Distance
import pandas as pd
from Environment import Environment


class JinaEmbeddings(Embeddings):
    def __init__(self, task="retrieval.document"):
        print("Creating Jina Embeddings instance...")
        self.model = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)
        print("Jina Embeddings instance created.")
        self.task = task

    def embed_documents(self, texts):
        return self.model.encode(texts, task=self.task, prompt_name=self.task)

    def embed_query(self, text):
        return self.model.encode([text], task="retrieval.query", prompt_name="retrieval.query")[0]


class RAG:
    def __init__(self, env: Environment):
        self.qdrant_client = QdrantClient(url=env.get_qdrant_url(), api_key=env.get_qdrant_api_key())
        self.collection_name = env.get_collection_name()
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
        self.retriever = self.qdrant.as_retriever(search_kwargs={"k": 3})
        # Reranker (from RerankerNoGroq notebook)
        print("Creating CrossEncoder model...")
        self.model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.model, top_n=3)
        print("Creating ContextualCompressionRetriever...")
        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor, base_retriever=self.retriever
        )

    def get_documents(self, question: str):
        compression_documents = self.compression_retriever.invoke(
            question
        )  # If no data found needs to still handle empty list.
        compression_contents = [doc.page_content for doc in compression_documents]
        df = pd.DataFrame({"contents": compression_contents})
        return df
