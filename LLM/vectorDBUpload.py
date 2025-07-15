import io
import os
from pathlib import Path
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from onc import ONC
from qdrant_client.models import PointStruct
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean
from unstructured.partition.pdf import partition_pdf

from LLM.RAG import JinaEmbeddings, QdrantClientWrapper

"""
Series of functions to preprocess PDF files, extract structured text chunks,
and embeds them using a Jina Model. Includes handler to upload embedded data to a vector database.

Usage for pdfs:
1. Call `process_pdf(use_pdf_bytes, file_path)` with the path to the PDF file and use_pdf_bytes False. use_pdf_bytes = True is for api route. Optionally source can be passed otherwise the file name is used.
2. Call `prepare_embedding_input(processing_results)` with a list of results from process_pdf. Optionally, you can pass a `JinaEmbeddings` instance to use a specific embedding model. If no embedding model is provided, a default instance will be created.
3. This function will return a list of dictionaries, each containing:
    - `embedding`: The embedding vector for the chunk.
    - `text`: The text content of the chunk.
    - `metadata`: Additional metadata source file and page number.
4. Call `upload_to_vector_db(resultsList, qdrant)` to upload the list of results to a Qdrant vector database.

Usage for collecting ONC device data and scraping URIs:
1. Call `get_device_info_from_onc_for_vdb(location_code)` with the desired location code to retrieve a list of devices and their information, 
    including device description scraped from the corresponding URI.
2. Use `prepare_embedding_input_from_preformatted(input, embedding_model)` to prepare the embedding input from the list of structured data obtained from get_device_info_from_onc_for_vdb.
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
    processing_results: list, embedding_model: JinaEmbeddings = None
):
    if embedding_model is None:
        embedding_model = JinaEmbeddings()

    task = "retrieval.passage"
    embedding_results = []
    chunks = [result["text"] for result in processing_results]
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
    input: list, embedding_model: JinaEmbeddings = None
):
    results = []

    for section in input:
        full_text = " ".join(section["paragraphs"])
        chunks = chunk_text(full_text)

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


def get_device_info_from_onc_for_vdb(location_code):
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)
    ONC_TOKEN = os.getenv("ONC_TOKEN")
    onc = ONC(ONC_TOKEN)

    params = {
        "locationCode": location_code,
    }
    devices = onc.getDevices(params)
    results = []
    for i in devices:
        i["LocationCode"] = location_code
        del i["deviceLink"]
        for j in i["cvTerm"]["device"]:
            if "uri" in j:
                j["description"] = getDeviceDefnFromURI(j["uri"])
                del j["uri"]
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
        collection_name=qdrant.collection_name, points=points
    )
