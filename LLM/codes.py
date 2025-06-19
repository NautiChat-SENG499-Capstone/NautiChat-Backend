import pandas as pd
import asyncio
from groq import Groq
import json
import pprint
from onc import ONC
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import httpx
from datasets import load_dataset
from langchain.docstore.document import Document
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from pathlib import Path
from Environment import Environment

env = Environment()

# Load API key and location code from .env
# env_path = Path(__file__).resolve().parent / ".env"
# load_dotenv(dotenv_path=env_path)
# ONC_TOKEN = os.getenv("ONC_TOKEN")
# CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")  # Change for a different location
# onc = ONC(ONC_TOKEN)
# cambridgeBayLocations = ["CBY", "CBYDS", "CBYIP", "CBYIJ", "CBYIU", "CBYSP", "CBYSS", "CBYSU", "CF240"]


async def generate_download_codes(deviceCategory: str, locationCode: str):
    """
    Returns a parameters object that includes the deviceCategory and locationCode so that
    the proper data can be downloaded.
    The parameters object is defined as follows:
    params = {
        "locationCode": {locationCode},
        "deviceCategoryCode": {deviceCategory},
        "dataProductCode": "TSSP",
        "extension": "csv",
        "dateFrom": {todayDate},
        "dateTo": {todayDate},
        "dpo_qualityControl": "1",
        "dpo_resample": "none",
    }
    """
    # property_API = (
    #     f"https://data.oceannetworks.ca/api/properties?locationCode={}&token={ONC_TOKEN}"
    # )

    params = {
        "locationCode": locationCode,
        "deviceCategoryCode": deviceCategory,
        "dataProductCode": "TSSP",
        "extension": "csv",
        "dateFrom": "2019-06-20T00:00:00.000Z",
        "dateTo": "2019-06-21T00:00:00.000Z",
        "dpo_qualityControl": "1",
        "dpo_resample": "none",
    }

    return json.dumps(params)

    # async with httpx.AsyncClient() as client:
    #     response = await client.get(property_API)
    #     response.raise_for_status()  # Error handling

    #     # Convert from JSON to Python dictionary for cleanup, return as JSON string
    #     raw_data = response.json()
    #     list_of_dicts = [
    #         {"description": item["description"], "propertyCode": item["propertyCode"]} for item in raw_data
    #     ]
    #     return json.dumps(list_of_dicts)