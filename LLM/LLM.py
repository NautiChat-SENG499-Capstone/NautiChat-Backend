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
from onc import ONC
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE") # change for a different location
model = "llama-3.3-70b-versatile"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class LLMPrompt:
    def __init__(self, prompt, retriever):
        self.prompt = prompt
        self.retriever = retriever

def get_documents(user_prompt):
  compression_documents = user_prompt.retriever.invoke(user_prompt.prompt)
  compression_contents = [doc.page_content for doc in compression_documents]
  df = pd.DataFrame({'contents': compression_contents})
  return df
"""
{
  "cvTerm": {
    "device": [
      {
        "uri": "http://vocab.nerc.ac.uk/collection/L22/current/TOOL1250/",
        "vocabulary": "SeaVoX Device Catalogue"
      }
    ]
  },
  "dataRating": [
    {
      "dateFrom": "2014-09-22T18:30:00.000Z",
      "dateTo": null,
      "samplePeriod": 5.0,
      "sampleSize": 1
    }
  ],
  "deviceCategoryCode": "ICEPROFILER",
  "deviceCode": "ASLSWIP53019",
  "deviceId": 23369,
  "deviceLink": "https://data.oceannetworks.ca/DeviceListing?DeviceId=23369",
  "deviceName": "ASL Shallow Water Ice Profiler 53019",
  "hasDeviceData": true
}"""

async def get_device_list():
    """Get a list of devices available at Cambridge Bay
        Returns a list of dictionaries turned into a string.
        Each Item in the list includes:
        - deviceName (str): Name of the device
        - deviceCode (str): Code of the device
        - deviceId (int): ID of the device
        - deviceLink (str): Link to the device
        - deviceCategoryCode (str): Category code of the device
        - hasDeviceData (bool): Whether the device has data
        - dataRating (list): List of data ratings for the device
        - cvTerm (dict): Controlled vocabulary term for the device
        example: '[{"deviceName": "ASL Shallow Water Ice Profiler 53019", "deviceCode": "ASLSWIP53019", "deviceId": 23369, "deviceLink": "https://data.oceannetworks.ca/DeviceListing?DeviceId=23369", "deviceCategoryCode": "ICEPROFILER", "hasDeviceData": true, "dataRating": [{"dateFrom": "2014-09-22T18:30:00.000Z", "dateTo": null, "samplePeriod": 5.0, "sampleSize": 1}], "cvTerm": {"device": [{"uri": "http://vocab.nerc.ac.uk/collection/L22/current/TOOL1250/", "vocabulary": "SeaVoX Device Catalogue"}]}}]'
    """
    onc = ONC(os.getenv("ONC_TOKEN"))
    params = {
        "locationCode": os.getenv("CAMBRIDGE_LOCATION_CODE"),
    }
    devices = onc.getDevices(params)

    # Convert to list of dictionaries
    list_of_dicts = [
        {
            "deviceName": device["deviceName"],
            "deviceCode": device["deviceCode"]
            "deviceId": device["deviceId"],
            "deviceLink": device["deviceLink"],
            "deviceCategoryCode": device["deviceCategoryCode"],
            "hasDeviceData": device["hasDeviceData"],
            "dataRating": device["dataRating"],
            "cvTerm": device["cvTerm"],

        } for device in devices
    ]
    return json.dumps(list_of_dicts)

async def get_properties_at_cambridge_bay():
    """Get a list of properties of data available at Cambridge Bay
        Returns a list of dictionaries turned into a string.
        Each Item in the list includes:
        - description (str): Description of the property. The description may have a colon in it.
        - propertyCode (str): Property Code of the property
        example: '{"Description of the property": Property Code of the property}'
    """
    property_API = f"https://data.oceannetworks.ca/api/properties?locationCode={CAMBRIDGE_LOCATION_CODE}&token={ONC_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.get(property_API)
        response.raise_for_status() # Error handling

        # Convert from JSON to Python dictionary for cleanup, return as JSON string
        raw_data = response.json()
        list_of_dicts = [
            {
                "description": item["description"],
                "propertyCode": item["propertyCode"]
            } for item in raw_data
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
    date_to_str: str = date_to.strftime("%Y-%m-%d") # Convert back to string

    async with httpx.AsyncClient() as client:
        # Get the data from ONC API
        temp_api = f"https://data.oceannetworks.ca/api/scalardata/location?locationCode={CAMBRIDGE_LOCATION_CODE}&deviceCategoryCode=CTD&propertyCode=seawatertemperature&dateFrom={day_str}&dateTo={date_to_str}&rowLimit=80000&outputFormat=Object&resamplePeriod=86400&token={ONC_TOKEN}"
        response = await client.get(temp_api)
        response.raise_for_status() # Error handling
        response = response.json()

    if response["sensorData"] is None:
      return ''
      return json.dumps({"result": "No data available for the given date."})

    data = response["sensorData"][0]["data"][0]

    # Get min, max, and average and store in dictionary
    return json.dumps({
        "daily_min": round(data["minimum"], 2),
        "daily_max": round(data["maximum"], 2),
        "daily_avg": round(data["value"], 2),
    })

async def run_conversation(user_prompt):
    # Initialize the conversation with system and user messages
    CurrentDate = datetime.now().strftime("%Y-%m-%d")
    messages=[
        {
            "role": "system",
            "content": f"You are an assistant for Oceans Network Canada that helps users access ONCs database via natural language.  \
            You can choose to use the given tools to obtain the data needed to answer the prompt and provide the results if that is required. \
            The current day is: {CurrentDate}."
        },
        {
            "role": "user",
            "content": user_prompt.prompt,
        },
        {"role": "system",
        "content": ""#Where Data retrieval from Vector DB will occur and be stored
        }
    ]
    # Define the available tools (i.e. functions) for our model to use
    tools = [
    {
      'type': 'function',
      'function': {
            'name': 'get_properties_at_cambridge_bay',
            'description': 'Get a list of properties of data available at Cambridge Bay. The function returns a list of dictionaries. Each Item in the list includes:\n        - description (str): Description of the property. The description may have a colon in it.\n        - propertyCode (str): Property Code of the property\n',
            'parameters': {
                'type': 'object',
                'properties': {
                  },
                }
            }
      },
    {
        'type': 'function',
        'function': {
          'name': 'get_daily_sea_temperature_stats_cambridge_bay',
          'description': 'Get daily sea temperature statistics for Cambridge Bay\nArgs:\n    day_str (str): Date in YYYY-MM-DD format',
          'parameters': {
              'properties': {
                  'day_str': {
                      'type': 'string',
                      'description': 'Date in YYYY-MM-DD format for when daily sea temperature is wanted for'
                      }
                  },
            'required': ['day_str'],
            'type': 'object'
            }
          }
     }
]
    vectorDBResponse = get_documents(user_prompt)
    messages[2] = ({"role": "system", "content": vectorDBResponse.to_string()})
    # Make the initial API call to Groq
    response = client.chat.completions.create(
        model=model, # LLM to use
        messages=messages, # Conversation history
        stream=False,
        tools=tools, # Available tools (i.e. functions) for our LLM to use
        tool_choice="auto", # Let our LLM decide when to use tools
        max_completion_tokens=4096, # Maximum number of tokens to allow in our response
        temperature=0.5 #A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
    )
    # Extract the response and any tool call responses
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        # Define the available tools that can be called by the LLM
        available_functions = {
            "get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            "get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
        }
        # Add the LLM's response to the conversation
        messages.append(response_message)

        # Process each tool call
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            # Call the tool and get the response
            function_response = await function_to_call(**function_args)
            # pprint(function_args.get("expression"))
            # if function_args.get("expression"):
            #     function_response = await function_to_call(
            #         expression=function_args.get("expression")
            #     )
            # else:
            #   function_response = await function_to_call()
            # Add the tool response to the conversation
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool", # Indicates this message is from tool use
                    "name": function_name,
                    "content": function_response,
                }
            )
            #pprint.pprint(messages)
        # Make a second API call with the updated conversation
        second_response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_completion_tokens=4096,
            temperature=0.5
        )#Calls LLM again with all the data from all functions
        # Return the final response
        return second_response.choices[0].message.content
    else:
        return response_message.content

async def main():

    load_dotenv()  # This loads the variables from .env

    # # Access the variables using os.getenv()
    # groq_api_key = os.getenv("GROQ_API_KEY")

    # ONC_TOKEN = os.getenv("ONC_TOKEN")
    # CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")

    # # Initialize Groq client
    # client = Groq(api_key=groq_api_key)
    # model = "llama-3.3-70b-versatile"

    

    df = load_dataset('gsnap88/ONCKnowledgeBase', split='train').to_pandas()


    documents = []
    for index, row in df.iterrows():
        text = f"Category: {row['category']}\nEntry: {row['entry']}\nEntry Contents: {row['entryContents']}"
        document = Document(page_content=text)
        documents.append(document)


    embeddings = HuggingFaceEmbeddings(model_name  = "BAAI/bge-base-en-v1.5")

    qdrant = Qdrant.from_documents(
    documents,
    embeddings,
    location=":memory:",  # Local mode with in-memory storage only
    collection_name="reranker",
    )

    retriever = qdrant.as_retriever(search_kwargs = {'k':3})
    model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
    compressor = CrossEncoderReranker(model=model, top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=retriever
    )
    user_prompt = "what is the temp at cambridge bay?"
    prompt = LLMPrompt(user_prompt, compression_retriever)
    response = await run_conversation(prompt)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())