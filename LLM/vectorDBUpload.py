import io
import os
from collections import Counter
from pathlib import Path
from uuid import uuid4

import fitz  # PyMuPDF
import nltk
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from nltk.tokenize import sent_tokenize
from onc import ONC
from qdrant_client.models import PointStruct
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean
from unstructured.partition.pdf import partition_pdf

from LLM.RAG import JinaEmbeddings, QdrantClientWrapper

import datetime
from qdrant_client.http.models import FieldCondition, Filter, MatchValue, PayloadSchemaType

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

Deprecated Usage for pdfs:
1. Call `deprecated_prepare_embedding_input(file_path)` with the path to the PDF file. Optionally, you can pass a `JinaEmbeddings` instance to use a specific embedding model. If no embedding model is provided, a default instance will be created.
2. This function will return a list of dictionaries, each containing:
   - `id`: Unique identifier for the chunk.
    - `embedding`: The embedding vector for the chunk.
    - `text`: The text content of the chunk.
    - `metadata`: Additional metadata source file, section heading, page number, and chunk index.
3. Call `upload_to_vector_db(resultsList, qdrant)` to upload the list of results to a Qdrant vector database.

Usage for collecting ONC device data and scraping URIs:
1. Call `get_device_info_from_onc_for_vdb(location_code)` with the desired location code to retrieve a list of devices and their information, 
    including device description scraped from the corresponding URI.
2. Use `prepare_embedding_input_from_preformatted(input, embedding_model)` to prepare the embedding input from the list of structured data obtained from get_device_info_from_onc_for_vdb.
3. Call `upload_to_vector_db(resultsList, qdrant)` to upload the list of results to a Qdrant vector database.

To speed up use assumes that the embedding model and qdrant client are being used from the RAG module.
"""


# Deprecated Preprocessing of PDFs functionality
def deprecated_extract_structured_chunks(file_path):
    doc = fitz.open(file_path)
    structured = []

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text
                for line in block["lines"]:
                    line_text = " ".join(span["text"] for span in line["spans"]).strip()
                    if not line_text:
                        continue
                    avg_font_size = sum(span["size"] for span in line["spans"]) / len(
                        line["spans"]
                    )
                    min_x = min(span["origin"][0] for span in line["spans"])
                    min_y = min(span["origin"][1] for span in line["spans"])
                    origin = (min_x, min_y)
                    structured.append(
                        {
                            "text": line_text,
                            "page": page_num,
                            "font_size": avg_font_size,
                            "origin": origin,
                        }
                    )
    structured.sort(key=lambda x: (x["origin"][1], x["origin"][0]))
    return structured


def deprecated_detect_main_body_font_size(structured_chunks):
    font_sizes = [round(chunk["font_size"], 1) for chunk in structured_chunks]
    font_size_counts = Counter(font_sizes)

    sorted_font_sizes = font_size_counts.most_common()

    # print("Detected font sizes (sorted by frequency):")
    # for size, count in sorted_font_sizes:
    # print(f"  Font size: {size} → {count} occurrences")

    # Assume the most common font size is the body text
    main_body_font_size = sorted_font_sizes[0][0] if sorted_font_sizes else None
    return main_body_font_size


def deprecated_group_sections(chunks):
    sections = []
    body_size = deprecated_detect_main_body_font_size(chunks)
    current_section = {"heading": None, "paragraphs": [], "page": []}

    for chunk in chunks:
        if chunk["font_size"] > body_size:
            if current_section["heading"] != None:
                sections.append(current_section)
                current_section = {
                    "heading": None,
                    "paragraphs": [],
                    "page": [chunk["page"]],
                }
            current_section["heading"] = chunk["text"]
        else:
            current_section["paragraphs"].append(chunk["text"])
        if chunk["page"] not in current_section["page"]:
            current_section["page"].append(chunk["page"])

    if current_section["paragraphs"] or current_section["heading"]:
        sections.append(current_section)

    return sections


# Default to small max tokens for better search and matching and faster
def deprecated_chunk_text_with_heading(text, heading="", max_tokens=300, overlap=50):
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab")
    sentences = sent_tokenize(text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        tokens = len(sentence.split())  # word-based token approximation
        # If adding this sentence would exceed the token limit
        if current_len + tokens > max_tokens:
            chunk_body = " ".join(current)
            chunk_text = f"{heading}\n{chunk_body}".strip()
            chunks.append(chunk_text)
            # Create overlap
            current = current[-overlap:] if overlap > 0 else []
            current_len = sum(len(s.split()) for s in current)

        current.append(sentence)
        current_len += tokens
    # Final chunk
    if current:
        chunk_body = " ".join(current)
        chunk_text = f"{heading}\n{chunk_body}".strip()
        chunks.append(chunk_text)
    return chunks


def deprecated_prepare_embedding_input(
    file_path: str, embedding_model: JinaEmbeddings = None
):
    structured_chunks = deprecated_extract_structured_chunks(file_path)
    sections = deprecated_group_sections(structured_chunks)
    results = []

    for section in sections:
        full_text = " ".join(section["paragraphs"])
        chunks = deprecated_chunk_text_with_heading(full_text, section["heading"])
        if embedding_model is None:
            embedding_model = JinaEmbeddings()
        embeddings = embedding_model.embed_documents(chunks)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            results.append(
                {
                    "id": f"{os.path.basename(file_path)}_chunk_{i}",
                    "embedding": embedding.tolist(),
                    "text": chunk,
                    "metadata": {
                        "source": os.path.basename(file_path),
                        "section_heading": section["heading"],
                        "page": section["page"],
                        "chunk_index": i,
                    },
                }
            )

    return results


# Updated Preprocessing of PDFs functionality


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
                    # "text": chunk,
                    "text":full_text,
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
        
        #If "dateTo" is None, replace with today's date
        if "dataRating" in i and isinstance(i["dataRating"], list):
            for rating_entry in i["dataRating"]:
                if isinstance(rating_entry, dict) and rating_entry.get("dateTo") is None:
                    today = datetime.datetime.now().isoformat()
                    rating_entry["dateTo"] = today
            

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


def sayHello():
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Hello from scheduled_vector_db_update!")

#Function gets called through APScheduler jobs to delete existing "ONC OCEANS 3.0 API" points and reupload with today's date
def vdb_auto_upload(app_state):

    qdrant_client_wrapper = app_state.rag.qdrant_client_wrapper

    #Create a payload index for "source" field (can't filter without this)
    qdrant_client_wrapper.qdrant_client.create_payload_index(
        collection_name=qdrant_client_wrapper.collection_name,
        field_name="source",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    filter_condition = Filter(
        must=[FieldCondition(key="source", match=MatchValue(value="ONC OCEANS 3.0 API"))]
    )
   
    qdrant_client_wrapper.qdrant_client.delete( 
        qdrant_client_wrapper.collection_name, points_selector=filter_condition
    )

    locationcodes = ["CBY", "CBYDS", "CBYIJ.J1", "CBYIJ.J2", "CBYIP", "CBYIP.D1", "CBYIP.D2", "CBYIP.D3", "CBYIP.D4", "CBYIP.K1", "CBYIP.K2", "CBYIP.K3", "CBYIU", "CBYIU.AC1", "CBYIU.AC2", "CBYIU.AC3",
                 "CBYIU.AC4", "CBYIU.AC5", "CBYSP", "CBYSS", "CBYSS.M1", "CBYSS.M2", "CBYSU", "CBYSU.AC1", "CBYSU.AC2", "CF240"]

    inputs = []
    for location_code in locationcodes:
        inputs.extend(get_device_info_from_onc_for_vdb(location_code=location_code)) 

    prepare_embedding_input = prepare_embedding_input_from_preformatted(input=inputs, embedding_model=JinaEmbeddings())

    upload_to_vector_db(prepare_embedding_input, qdrant_client_wrapper)


