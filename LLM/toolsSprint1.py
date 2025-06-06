import pandas as pd
import asyncio
from groq import Groq
import json
import os
import pprint
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

# Load API key and location code from .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")  # Change for a different location


async def get_properties_at_cambridge_bay():
    """Get a list of properties of data available at Cambridge Bay
    Returns a list of dictionaries turned into a string.
    Each Item in the list includes:
    - description (str): Description of the property. The description may have a colon in it.
    - propertyCode (str): Property Code of the property
    example: '{"Description of the property": Property Code of the property}'
    """
    property_API = (
        f"https://data.oceannetworks.ca/api/properties?locationCode={CAMBRIDGE_LOCATION_CODE}&token={ONC_TOKEN}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(property_API)
        response.raise_for_status()  # Error handling

        # Convert from JSON to Python dictionary for cleanup, return as JSON string
        raw_data = response.json()
        list_of_dicts = [
            {"description": item["description"], "propertyCode": item["propertyCode"]} for item in raw_data
        ]
        return json.dumps(list_of_dicts)


async def get_daily_sea_temperature_stats_cambridge_bay(day_str: str):
    """
    Get daily sea temperature statistics for Cambridge Bay
    Args:
        day_str (str): Date in YYYY-MM-DD format
    """
    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = datetime.strptime(day_str, "%Y-%m-%d") + timedelta(days=1)
    date_to_str: str = date_to.strftime("%Y-%m-%d")  # Convert back to string
    print(day_str)

    async with httpx.AsyncClient() as client:
        # Get data from ONC API
        temp_api = f"https://data.oceannetworks.ca/api/scalardata/location?locationCode={CAMBRIDGE_LOCATION_CODE}&deviceCategoryCode=CTD&propertyCode=seawatertemperature&dateFrom={day_str}&dateTo={date_to_str}&rowLimit=80000&outputFormat=Object&resamplePeriod=86400&token={ONC_TOKEN}"
        response = await client.get(temp_api)
        response.raise_for_status()  # Error handling
        response = response.json()

    if response["sensorData"] is None:
        return ""
        return json.dumps({"result": "No data available for the given date."})

    data = response["sensorData"][0]["data"][0]

    # Get min, max, and average and store in dictionary
    return json.dumps(
        {
            "daily_min": round(data["minimum"], 2),
            "daily_max": round(data["maximum"], 2),
            "daily_avg": round(data["value"], 2),
        }
    )
=======
import pandas as pd
import asyncio
from groq import Groq
import json
import os
import pprint
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
# Load API key and location code from .env
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE") # Change for a different location

async def get_properties_at_cambridge_bay():
    """Get a list of properties of data available at Cambridge Bay
    Returns a list of dictionaries turned into a string.
    Each Item in the list includes:
    - description (str): Description of the property. The description may have a colon in it.
    - propertyCode (str): Property Code of the property
    example: '{"Description of the property": Property Code of the property}'
    """
    property_API = (
        f"https://data.oceannetworks.ca/api/properties?locationCode={CAMBRIDGE_LOCATION_CODE}&token={ONC_TOKEN}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(property_API)
        response.raise_for_status()  # Error handling

        # Convert from JSON to Python dictionary for cleanup, return as JSON string
        raw_data = response.json()
        list_of_dicts = [
            {"description": item["description"], "propertyCode": item["propertyCode"]} for item in raw_data
        ]
        return json.dumps(list_of_dicts)


async def get_daily_sea_temperature_stats_cambridge_bay(day_str: str):
    """
    Get daily sea temperature statistics for Cambridge Bay
    Args:
        day_str (str): Date in YYYY-MM-DD format
    """
    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = datetime.strptime(day_str, "%Y-%m-%d") + timedelta(days=1)
    date_to_str: str = date_to.strftime("%Y-%m-%d")  # Convert back to string

    async with httpx.AsyncClient() as client:
        # Get the data from ONC API
        temp_api = f"https://data.oceannetworks.ca/api/scalardata/location?locationCode={CAMBRIDGE_LOCATION_CODE}&deviceCategoryCode=CTD&propertyCode=seawatertemperature&dateFrom={day_str}&dateTo={date_to_str}&rowLimit=80000&outputFormat=Object&resamplePeriod=86400&token={ONC_TOKEN}"
        response = await client.get(temp_api)
        response.raise_for_status()  # Error handling
        response = response.json()

    if response["sensorData"] is None:
        return ""
        return json.dumps({"result": "No data available for the given date."})

    data = response["sensorData"][0]["data"][0]

    # Get min, max, and average and store in dictionary
    return json.dumps(
        {
            "daily_min": round(data["minimum"], 2),
            "daily_max": round(data["maximum"], 2),
            "daily_avg": round(data["value"], 2),
        }
    )
