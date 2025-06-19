from langchain_qdrant import Qdrant  
from qdrant_client import QdrantClient
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from qdrant_client.http.models import VectorParams, Distance
import pandas as pd
from LLM.Environment import Environment


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
    def __init__(
        self,
        env: Environment,
        *,
        embedder: Embeddings | None = None,
        cross_encoder: HuggingFaceCrossEncoder | None = None,
        qdrant_client: QdrantClient | None = None,
    ):
        self.qdrant_client_wrapper = QdrantClientWrapper(env)
        self.qdrant_client = qdrant_client or self.qdrant_client_wrapper.qdrant_client
        self.collection_name = self.qdrant_client_wrapper.collection_name

        self.embedding = embedder or JinaEmbeddings()

        self.qdrant = Qdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.embedding,
            content_payload_key="text",
        )

        self.retriever = self.qdrant.as_retriever(search_kwargs={"k": 3})
        self.cross_encoder = cross_encoder or HuggingFaceCrossEncoder(
            model_name="BAAI/bge-reranker-base"
        )
        self.compressor = CrossEncoderReranker(model=self.cross_encoder, top_n=3)

        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor, base_retriever=self.retriever
        )

    def get_documents(self, question: str) -> pd.DataFrame:
        docs = self.compression_retriever.invoke(question)
        contents = [d.page_content for d in docs]
        return pd.DataFrame({"contents": contents})
