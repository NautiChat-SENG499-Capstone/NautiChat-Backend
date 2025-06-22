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

# Load API key and location code from .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")  # Change for a different location
onc = ONC(ONC_TOKEN)
cambridgeBayLocations = ["CBY", "CBYDS", "CBYIP", "CBYIJ", "CBYIU", "CBYSP", "CBYSS", "CBYSU", "CF240"]


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


async def get_deployed_devices_over_time_interval(dateFrom: str, dateTo: str):
    """
    Get the devices at cambridge bay deployed over the specified time interval including sublocations
    Returns:
        JSON string: List of deployed devices and their metadata Each item includes:
            - begin (str): deployment start time
            - end (str): deployment end time
            - deviceCode (str)
            - deviceCategoryCode (str)
            - locationCode (str)
            - citation (dict): citation metadata (includes description, doi, etc)
    Args:
        dateFrom (str): ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')
        dateTo (str): ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')
    """
    deployedDevices = []
    for locationCode in cambridgeBayLocations:
        params = {
            "locationCode": locationCode,
            "dateFrom": dateFrom,
            "dateTo": dateTo,
        }
        try:
            response = onc.getDeployments(params)
        except Exception as e:
            if e.response.status_code == 404:
                # print(f"Warning: No deployments found for locationCode {locationCode}")
                continue
            else:
                raise  # re-raise if different error
        for deployment in response:
            if deployment is None:
                continue
            device_info = {
                "begin": deployment["begin"],
                "end": deployment["end"],
                "deviceCode": deployment["deviceCode"],
                "deviceCategoryCode": deployment["deviceCategoryCode"],
                "locationCode": deployment["locationCode"],
                "citation": deployment["citation"],
            }
            deployedDevices.append(device_info)

    if deployedDevices == []:
        return json.dumps({"result": "No data available for the given date."})

    return json.dumps(deployedDevices)

async def get_active_instruments_at_cambridge_bay():
    """
    Get the number of instruments collecting data at Cambridge Bay over the specified interval.
    Uses the ONC Python client to access deployment and stream data.

    Returns:
        JSON string: Dictionary with count and optional metadata.
            {
                "activeInstrumentCount": int,
                "details": [ ... ]
            }
    """
    active_instruments = []
    deployed_device_count = 0

    for locationCode in cambridgeBayLocations:
        params = {
            "locationCode": locationCode,
        }
        try:
            deployments = onc.getDeployments(params)
        except Exception:
            continue # Skip any failure silently

        if not deployments:
            continue

        for device in deployments:
            if device.get("end") is not None:
                continue  # deployment is not ongoing
            deployed_device_count = deployed_device_count + 1
            active_instruments.append(device)
    result = {
        "activeInstrumentCount": deployed_device_count,
        "details": active_instruments,
    }
    return json.dumps(result)

# async def get_time_range_of_available_data(deviceCategoryCode: str):
#     """
#     Get all deployment time ranges (begin and end times) at Cambridge Bay for a specific device category.
#     Returns:
#         JSON string: Sorted list of (begin, end) tuples as ISO strings.
#     """
#     time_ranges = []

#     for locationCode in cambridgeBayLocations:
#         params = {
#             "locationCode": locationCode,
#             "deviceCategoryCode": deviceCategoryCode,
#         }
#         try:
#             deployments = onc.getDeployments(params)
#         except Exception:
#             continue  # Skip any errors silently

#         for device in deployments:
#             begin = device.get("begin")
#             end = device.get("end")
#             if begin:
#                 time_ranges.append((begin, end))

#     time_ranges.sort(key=lambda x: datetime.fromisoformat(x[0].replace("Z", "+00:00")))
#     return json.dumps(time_ranges)