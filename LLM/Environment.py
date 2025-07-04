import os
import random
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
        self.__groq_keys = self.__get_groq_api_keys_from_pool() # initialize the groq api token randomly from pool
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME")
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

    def get_collection_name(self):
        return self.collection_name

    def get_qdrant_api_key(self):
        return self.qdrant_api_key
    
    # This function initializes the Groq API Key and also sets up a list so that they can be cycled through and removed as they run out of tokens.
    def __get_groq_api_keys_from_pool(self):
        key_str = os.getenv("GROQ_API_KEY")
        groq_keys = [key.strip() for key in key_str.split(",") if key.strip()]
        new_api_key = random.choice(groq_keys)
        groq_keys.remove(new_api_key)
        self.client = Groq(api_key=new_api_key)
        return groq_keys

    # This function cycles to a new Groq API token. It can be used in the event that an LLM call runs out of tokens.
    def cycle_new_groq_api_key(self):
        new_api_key = random.choice(self.__groq_keys)
        self.__groq_keys.remove(new_api_key)
        self.client = Groq(api_key=random.choice(self.__groq_keys))
