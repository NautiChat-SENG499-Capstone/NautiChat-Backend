import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


class Environment:
    def __init__(self):
        # If we're in production, we assume environment variables are set
        # If not, we load them from a .env file
        if os.getenv("ENV") != "production":
            env_file_location = str(Path(__file__).resolve().parent / ".env")
            load_dotenv(env_file_location)
        self.onc_token = os.getenv("ONC_TOKEN")
        self.location_code = os.getenv("CAMBRIDGE_LOCATION_CODE")
        self.model = "llama-3.3-70b-versatile"
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.knowledge_collection_name = os.getenv("QDRANT_COLLECTION_NAME")
        self.QA_collection_name = os.getenv("QDRANT_QA_COLLECTION")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")

    def get_onc_token(self):
        return self.onc_token

    def get_location_code(self):
        return self.location_code

    def get_model(self):
        return self.model

    def get_client(self):
        return self.client

    def get_qdrant_url(self):
        return self.qdrant_url

    def get_knowledge_collection_name(self):
        return self.knowledge_collection_name
    
    def get_QA_collection_name(self):
        return self.QA_collection_name

    def get_qdrant_api_key(self):
        return self.qdrant_api_key
