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
from toolsSprint1 import get_properties_at_cambridge_bay, get_daily_sea_temperature_stats_cambridge_bay
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

# Initialize Groq client using Llama 3.3
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

# Construct conversation that includes system prompt, user prompt, and results from vector DB
async def run_conversation(user_prompt):
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

    # Define available tools (i.e. functions) for model to use
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
    # Make initial API call to Groq
    response = client.chat.completions.create(
        model=model, # LLM to use
        messages=messages, # Conversation history
        stream=False,
        tools=tools, # Available tools (i.e. functions) for LLM to use
        tool_choice="auto", # Let LLM decide when to use tools
        max_completion_tokens=4096, # Maximum number of tokens to allow in response
        temperature=0.5 #A temperature of 1=default balance between randomness and confidence. Less than 1 is less randomness, Greater than is more randomness
    )

    # Extract the response and any tool call responses
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        # Define available tools that can be called by the LLM
        available_functions = {
            "get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            "get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
        }
        # Add LLM's response to the conversation
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
        )# Calls LLM again with all the data from all functions
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

    # Load ONC dataset and convert into Document objects for vector embedding
    df = load_dataset('gsnap88/ONCKnowledgeBase', split='train').to_pandas()

    documents = []
    for index, row in df.iterrows():
        text = f"Category: {row['category']}\nEntry: {row['entry']}\nEntry Contents: {row['entryContents']}"
        document = Document(page_content=text)
        documents.append(document)

    # Embed documents
    embeddings = HuggingFaceEmbeddings(model_name  = "BAAI/bge-base-en-v1.5")
    # Store embedded documents in a Qdrant vector DB
    qdrant = Qdrant.from_documents(
    documents,
    embeddings,
    location=":memory:",  # Local mode with in-memory storage only
    collection_name="reranker",
    )

    # Wrap reranker in retriever - two-stage retrieval process
    retriever = qdrant.as_retriever(search_kwargs = {'k':3})
    model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
    compressor = CrossEncoderReranker(model=model, top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=retriever
    )

    user_prompt = "What was the maximum temperature at cambridge bay yesterday?"
    # Combine question with retriever for downstream use
    prompt = LLMPrompt(user_prompt, compression_retriever)
    response = await run_conversation(prompt)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())