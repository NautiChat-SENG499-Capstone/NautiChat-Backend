import pandas as pd
import asyncio
from groq import Groq
import json
import os
from datetime import datetime, timedelta
from toolsSprint1 import get_properties_at_cambridge_bay, get_daily_sea_temperature_stats_cambridge_bay
from dotenv import load_dotenv
import httpx
from pathlib import Path
from RAG import RAG
from Constants.toolDescriptions import tools
from gettingDevicesAndData import get_devices_info, get_scalar_data_by_device

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")  # change for a different location
model = "llama-3.3-70b-versatile"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def run_conversation(user_prompt, RAG_instance: RAG):
    # Initialize the conversation with system and user messages
    CurrentDate = datetime.now().strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": f"You are an assistant for Oceans Network Canada that helps users access ONCs database via natural language.  \
            You can choose to use the given tools to obtain the data needed to answer the prompt and provide the results if that is required. Dont provide the results in JSON format. Make it readable! \
            The current day is: {CurrentDate}.",
        },
        {
            "role": "user",
            "content": user_prompt,
        },
        {"role": "system", "content": ""},  # Where Data retrieval from Vector DB will occur and be stored
    ]
    # Define the available tools (i.e. functions) for our model to use
    #print("Tools defined successfully.")
    vectorDBResponse = RAG_instance.get_documents(user_prompt)
    messages[2] = {"role": "system", "content": vectorDBResponse.to_string()}
    # Make the initial API call to Groq
    response = client.chat.completions.create(
        model=model,  # LLM to use
        messages=messages,  # Conversation history
        stream=False,
        tools=tools,  # Available tools (i.e. functions) for our LLM to use
        tool_choice="auto",  # Let our LLM decide when to use tools
        max_completion_tokens=4096,  # Maximum number of tokens to allow in our response
        temperature=0.5,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
    )
    # Extract the response and any tool call responses
    response_message = response.choices[0].message
    #print("Response received from Groq API.")
    #print("Response message:", response_message)
    tool_calls = response_message.tool_calls
    if tool_calls:
        # Define the available tools that can be called by the LLM
        available_functions = {
            #"get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            #"get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
            "get_scalar_data_by_device": get_scalar_data_by_device,
            "get_devices_info": get_devices_info,
        }
        # Add the LLM's response to the conversation
        messages.append(response_message)

        # Process each tool call
        #print("Processing tool calls...")
        #print("Tool calls:", tool_calls)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            # Call the tool and get the response
            function_response = await function_to_call(**function_args)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",  # Indicates this message is from tool use
                    "name": function_name,
                    "content": function_response,
                }
            )
        # Make a second API call with the updated conversation
        second_response = client.chat.completions.create(
            model=model, messages=messages, stream=False, tools=tools, tool_choice="auto", max_completion_tokens=4096, temperature=0.5
        )  # Calls LLM again with all the data from all functions
        # Return the final response
        #print("Second response received from Groq API.")
        #print("Second response message:", second_response.choices)
        return second_response.choices[0].message.content
    else:
        return response_message.content


async def main():

    qdrant_url=os.getenv("QDRANT_URL")
    collection_name=os.getenv("QDRANT_COLLECTION_NAME")
    qdrant_api_key=os.getenv("QDRANT_API_KEY")

    RAG_instance = RAG(
        qdrant_url=qdrant_url,
        collection_name=collection_name,
        qdrant_api_key=qdrant_api_key
    )
    print("RAG instance created successfully.")
    user_prompt = "what properties are available at Cambridge Bay?"
    user_prompt = input("Enter your next question (or 'exit' to quit): ")
    while user_prompt not in ["", "exit"]:
        try:
            response = await run_conversation(user_prompt, RAG_instance)
            print(response)
        except Exception as e:
            print("Error occurred:", e)
        user_prompt = input("Enter your next question (or 'exit' to quit): ")


if __name__ == "__main__":
    asyncio.run(main())
