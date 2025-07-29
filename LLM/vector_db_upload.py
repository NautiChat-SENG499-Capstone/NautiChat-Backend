import io
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Union
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from onc import ONC
from qdrant_client.http.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
)
from qdrant_client.models import PointStruct
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean
from unstructured.partition.pdf import partition_pdf

from LLM.RAG import JinaEmbeddings, QdrantClientWrapper

"""
Series of functions to preprocess PDF files + json files, extract structured text chunks,
and embeds them using a Jina Model. Includes handler to upload embedded data to a vector database.

Usage for pdfs (or json's):
1a. Call `process_pdf(use_pdf_bytes, file_path)` with the path to the PDF file and use_pdf_bytes False. use_pdf_bytes = True is for api route. Optionally source can be passed otherwise the file name is used.
1b. Call `process_json(use_json_bytes, file_path)` with the path to the json file and use_json_bytes False. use_json_bytes = True is for api route. Optionally source can be passed otherwise the file name is used. 
2. Call `prepare_embedding_input(processing_results)` with a list of results from process_pdf. Optionally, you can pass a `JinaEmbeddings` instance to use a specific embedding model Optionally you can pass the embedding_field to specify the field name to embed and vectorize, the default is "text". If no embedding model is provided, a default instance will be created.
3. This function will return a list of dictionaries, each containing:
    - `embedding`: The embedding vector for the chunk.
    - `text`: The text content of the chunk.
    - `metadata`: Additional metadata source file and page number.
4. Call `upload_to_vector_db(resultsList, qdrant)` to upload the list of results to a Qdrant vector database.

Usage for collecting ONC device data and scraping URIs:
1. Call `get_device_info_from_onc_for_vdb(location_code)` with the desired location code to retrieve a list of devices and their information, 
    including device description scraped from the corresponding URI.
2. Use `prepare_embedding_input_from_preformatted(input)` to prepare the embedding input from the list of structured data obtained from get_device_info_from_onc_for_vdb. Optionally you can provide a JinaEmbedding Instance otherwise one is created. Optionally you can change doChunking to False to not split data into chunks.
3. Call `upload_to_vector_db(resultsList, qdrant)` to upload the list of results to a Qdrant vector database.

To speed up use assumes that the embedding model and qdrant client are being used from the RAG module.
"""

# Preprocessing of PDFs functionality


def process_pdf(use_pdf_bytes: bool, input_file, source: str = ""):
    if use_pdf_bytes:
        elements = partition_pdf(
            file=io.BytesIO(input_file), strategy="fast", infer_table_structure=True
        )
    else:
        elements = partition_pdf(
            filename=input_file, strategy="fast", infer_table_structure=True
        )

    # for i, el in enumerate(elements):
    #  print(f"{i:>2} | category: {getattr(el, 'category', None)} | text: {el.text}")

    # Clean up text
    for el in elements:
        if el.text:
            el.text = clean(el.text, extra_whitespace=True, dashes=True)
    # Filter out empty elements
    elements = [el for el in elements if el.text and len(el.text.strip()) > 1]

    # Get source name
    if source == "":
        source = os.path.basename(input_file)

    # Chunk by semantic structure (titles, etc.)
    chunks = chunk_by_title(
        elements,
        max_characters=1024,
        overlap=150,
        multipage_sections=True,
        combine_text_under_n_chars=400,
    )
    results = []
    for chunk in chunks:
        results.append(
            {
                "text": chunk.text.strip(),
                "metadata": {
                    "source": source,
                    "page_number": getattr(chunk.metadata, "page_number", None),
                    "category": chunk.category,
                },
            }
        )
    return results


def chunk_text(text, max_characters=1024, overlap=150):
    chunks = []
    while len(text) > max_characters:
        chunks.append(text[:max_characters])
        text = text[max_characters - overlap :]
    chunks.append(text)
    return chunks


def prepare_embedding_input(
    processing_results: list,
    embedding_model: JinaEmbeddings = None,
    embedding_field="text",
):
    if embedding_model is None:
        embedding_model = JinaEmbeddings()

    task = "retrieval.passage"
    embedding_results = []
    chunks = [result[embedding_field] for result in processing_results]

    embeddings = embedding_model.embed_documents(chunks)

    for embedding, result in zip(embeddings, processing_results):
        embedding_results.append(
            {
                "embedding": embedding.tolist(),
                "text": result["text"],
                "metadata": {
                    "source": result["metadata"]["source"],
                    "page": result["metadata"]["page_number"],
                },
            }
        )

    return embedding_results


# Collection and preprocessing of ONC device data functionality


# input must be of form [{'paragraphs': ['...', '...'], 'page': [1, 2, ...], 'source': '...'}, ...]
def prepare_embedding_input_from_preformatted(
    input: list, embedding_model: JinaEmbeddings = None, doChunking: bool = True
):
    results = []

    for section in input:
        full_text = " ".join(section["paragraphs"])
        if doChunking:
            chunks = chunk_text(full_text)
        else:
            chunks = [full_text]

        if embedding_model is None:
            embedding_model = JinaEmbeddings()
        embeddings = embedding_model.embed_documents(chunks)

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            results.append(
                {
                    "embedding": embedding.tolist(),
                    "text": chunk,
                    "metadata": {
                        "source": section["source"],
                        "page": section["page"],
                    },
                }
            )

    return results


def getDeviceDefnFromURI(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data from {url}")

    soup = BeautifulSoup(response.text, "html.parser")

    definition_row = soup.find("th", string="Definition")
    if definition_row:
        definition_text = definition_row.find_next_sibling("td").text.strip()
    else:
        definition_text = ""

    return definition_text


def get_device_deployments_from_onc_for_vdb(location_code):
    # Gets data on devices from deployment endpoint
    # Collects data available times by device category code
    # Combines overlapping time intervals, including those with less than 24 hours seperation
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)
    ONC_TOKEN = os.getenv("ONC_TOKEN")
    onc = ONC(ONC_TOKEN)

    params = {
        "locationCode": location_code,
    }
    devices = onc.getDeployments(params)

    merged = {}
    curtime = datetime.now()
    for item in devices:
        deviceCategoryCode = item["deviceCategoryCode"]
        begin = datetime.strptime(item["begin"], "%Y-%m-%dT%H:%M:%S.%fZ")
        if item["end"] is None:
            end = curtime
        else:
            end = datetime.strptime(item["end"], "%Y-%m-%dT%H:%M:%S.%fZ")
        if deviceCategoryCode not in merged:
            # Initialize merged entry with selected fields only
            merged[deviceCategoryCode] = {
                "deviceCategoryCode": deviceCategoryCode,
                "dates": [{"begin": begin, "end": end}],
            }
        else:
            matchFound = False
            # Find and merge any overlapping intervals
            for date in merged[deviceCategoryCode]["dates"]:
                if matchFound:
                    break
                elif (
                    begin < date["begin"]
                    and date["begin"] <= end + timedelta(days=1)
                    and end <= date["end"]
                ):
                    date["begin"] = begin
                    matchFound = True
                elif begin <= date["begin"] and date["end"] <= end:
                    date["begin"] = begin
                    date["end"] = end
                    matchFound = True
                elif begin >= date["begin"] and date["end"] >= end:
                    matchFound = True
                elif (
                    date["begin"] <= begin
                    and begin <= date["end"] + timedelta(days=1)
                    and date["end"] < end
                ):
                    date["end"] = end
                    matchFound = True
            if not matchFound:
                merged[deviceCategoryCode]["dates"].append({"begin": begin, "end": end})

    for code in merged:
        latestEnd = merged[code]["dates"][0]["end"]
        for date in merged[code]["dates"]:
            if latestEnd < date["end"]:
                latestEnd = date["end"]
            date["begin"] = str(date["begin"])
            date["end"] = str(date["end"])
        merged[code]["MostRecentData"] = str(latestEnd)

    return merged


def get_device_info_from_onc_for_vdb(location_code):
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)
    ONC_TOKEN = os.getenv("ONC_TOKEN")
    onc = ONC(ONC_TOKEN)

    params = {
        "locationCode": location_code,
    }
    devices = onc.getDevices(params)
    merged = {}

    for item in devices:
        deviceCategoryCode = item["deviceCategoryCode"]

        if deviceCategoryCode not in merged:
            # Initialize merged entry with selected fields only
            merged[deviceCategoryCode] = {
                "cvTerm": item["cvTerm"],
                "dataRating": item["dataRating"],
                "deviceCategoryCode": deviceCategoryCode,
                "deviceCode": item["deviceCode"],
                "deviceName": item["deviceName"],
                "hasDeviceData": item["hasDeviceData"],
            }
        else:
            merged[deviceCategoryCode]["dataRating"].extend(item["dataRating"])

    devices = list(merged.values())
    deployments = get_device_deployments_from_onc_for_vdb(location_code)
    results = []
    for i in devices:
        i["LocationCode"] = location_code

        for j in i["cvTerm"]["device"]:
            if "uri" in j:
                j["description"] = getDeviceDefnFromURI(j["uri"])
                del j["uri"]

        i.pop("dataRating", None)

        i["DataAvailableDates"] = deployments[i["deviceCategoryCode"]]["dates"]
        i["MostRecentData"] = deployments[i["deviceCategoryCode"]]["MostRecentData"]

        results.append(
            {"paragraphs": [str(i)], "page": [], "source": "ONC OCEANS 3.0 API"}
        )
    return results


def upload_to_vector_db(resultsList: list, qdrant: QdrantClientWrapper):
    points = []
    for item in resultsList:
        points.append(
            PointStruct(
                id=uuid4().hex,
                vector=item["embedding"],
                payload={"text": item["text"], **item["metadata"]},
            )
        )

    qdrant.qdrant_client.upload_points(
        collection_name=qdrant.general_collection_name, points=points
    )


def format_value(value: Any) -> str:
    """Format a single value for display."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


def process_dict(
    d: dict, prefix: str = "", exclude_fields: list[str] = None
) -> list[str]:
    """Process a dictionary into field: value lines."""
    exclude_fields = exclude_fields or []
    lines = []

    for key, value in d.items():
        if key in exclude_fields:
            continue

        full_key = f"{prefix}{key}" if prefix else key

        if isinstance(value, dict):
            lines.extend(process_dict(value, f"{full_key}_", exclude_fields))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    lines.extend(process_dict(item, f"{full_key}_{i}_", exclude_fields))
                else:
                    lines.append(f"{full_key}_{i}: {format_value(item)}")
        else:
            lines.append(f"{full_key}: {format_value(value)}")

    return lines


def json_to_text(data: Union[dict, list, Any], exclude_fields: list[str] = None) -> str:
    """Convert any JSON data to simple 'field: value' text format."""
    exclude_fields = exclude_fields or []

    if isinstance(data, dict):
        return "\n".join(process_dict(data, "", exclude_fields))
    elif isinstance(data, list):
        if len(data) == 1:
            return json_to_text(data[0], exclude_fields)
        else:
            result = []
            for i, item in enumerate(data):
                result.append(f"Item {i}:")
                result.append(json_to_text(item, exclude_fields))
                result.append("")
            return "\n".join(result)
    else:
        return str(data)


def process_json(
    use_json_bytes: bool, input_file, source: str = "", exclude_fields: list[str] = []
):
    """
    Process JSON file/data into structured text chunks for embedding.

    Args:
        use_json_bytes: If True, input_file is bytes data; if False, it's a file path
        input_file: Either file path (string) or bytes data
        source: Source identifier (defaults to filename if empty)
        exclude_fields: List of field names to exclude from processing

    Returns:
        List of dictionaries with 'text' and 'metadata' for embedding
    """
    exclude_fields = exclude_fields or []

    # Load JSON data
    if use_json_bytes:
        if isinstance(input_file, bytes):
            json_data = json.loads(input_file.decode("utf-8"))
        else:
            json_data = json.loads(input_file)
        source = source or "uploaded_json"
    else:
        with open(input_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        source = source or os.path.basename(input_file)

    results = []

    # Handle single object vs array
    if isinstance(json_data, list):
        for i, item in enumerate(json_data):
            full_json_as_text = json.dumps(item, indent=2)
            text = json_to_text(item, exclude_fields)
            if text.strip():  # Only add non-empty text
                results.append(
                    {
                        "embedding_text": text,
                        "text": full_json_as_text,
                        "metadata": {
                            "source": source,
                            "page_number": i,
                            "total_pages": len(json_data),
                        },
                    }
                )
    else:
        full_json_as_text = json.dumps(json_data, indent=2)
        text = json_to_text(json_data, exclude_fields)
        if text.strip():  # Only add non-empty text
            results.append(
                {
                    "embedding_text": text,
                    "text": full_json_as_text,
                    "metadata": {"source": source, "page_number": 0, "total_pages": 1},
                }
            )
    return results


# Returns current time for vdb_auto_upload
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


# Function gets called through APScheduler jobs to delete existing "ONC OCEANS 3.0 API" points and reupload with today's date
# Uploads to ONC-General
# APScheduler job in lifespan.py calls this every 24 hours
def vdb_auto_upload(app_state):
    try:
        print(f"{get_current_time()} vector DB auto upload - START")
        qdrant_client_wrapper = app_state.rag.qdrant_client_wrapper

        locationcodes_str = os.getenv("location_codes")
        if locationcodes_str:
            locationcodes = [code.strip() for code in locationcodes_str.split(",")]
        else:
            locationcodes = []
            print(
                f"{get_current_time()} vector DB auto upload - END - WARN: 'location_codes' not found in .env or is empty. No locations to process."
            )
            return  # Exit if no codes to process

        # Create a payload index for "source" field (can't filter without this)
        qdrant_client_wrapper.qdrant_client.create_payload_index(
            collection_name=qdrant_client_wrapper.general_collection_name,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD,
        )

        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="source", match=MatchValue(value="ONC OCEANS 3.0 API")
                )
            ]
        )

        # Getting a count of how many points we're deleting just to print
        filtered_points = qdrant_client_wrapper.qdrant_client.count(
            collection_name=qdrant_client_wrapper.general_collection_name,
            count_filter=filter_condition,
            exact=True,
        )

        print(
            f"{get_current_time()} vector DB auto upload - Deleting {filtered_points.count} points from {qdrant_client_wrapper.general_collection_name}"
        )
        qdrant_client_wrapper.qdrant_client.delete(
            qdrant_client_wrapper.general_collection_name,
            points_selector=filter_condition,
        )

        print(
            f"{get_current_time()} vector DB auto upload - Calling ONC API for devices"
        )
        inputs = []
        for location_code in locationcodes:
            inputs.extend(get_device_info_from_onc_for_vdb(location_code=location_code))

        prepare_embedding_input = prepare_embedding_input_from_preformatted(
            input=inputs, embedding_model=JinaEmbeddings(), doChunking=False
        )

        print(
            f"{get_current_time()} vector DB auto upload - Uploading {len(prepare_embedding_input)} points to {qdrant_client_wrapper.general_collection_name}"
        )
        upload_to_vector_db(prepare_embedding_input, qdrant_client_wrapper)
        print(f"{get_current_time()} vector DB auto upload - END")
    except Exception as e:
        print(
            f"{get_current_time()} vector DB auto upload - ERROR: An error occurred: {e}"
        )
