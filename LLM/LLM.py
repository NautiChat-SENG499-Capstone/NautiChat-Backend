from datetime import datetime
import logging
import sys
import pandas as pd
import json
from collections import OrderedDict
from Environment import Environment
import asyncio

from toolsSprint1 import (
    get_properties_at_cambridge_bay,
    get_daily_sea_temperature_stats_cambridge_bay,
    get_deployed_devices_over_time_interval,
    get_active_instruments_at_cambridge_bay,
    # get_time_range_of_available_data,
)
from toolsSprint2 import (
    get_daily_air_temperature_stats_cambridge_bay,
    get_oxygen_data_24h,
    # get_ship_noise_acoustic_for_date,
    get_wind_speed_at_timestamp,
    get_ice_thickness,
)
from Constants.statusCodes import StatusCode
from schemas import RunConversationResponse, ObtainedParamsDictionary
from dataDownload import generate_download_codes
from RAG import RAG
from Constants.toolDescriptions import toolDescriptions


logger = logging.getLogger(__name__)

sys.modules["LLM"] = sys.modules[__name__]

class LLM:
    #__shared: dict[str, object] | None = None
    # singleton cache
    

    def __init__(self, env, *, RAG_instance=None):
        self.env = env
        self.client = env.get_client()
        self.model = env.get_model()
        #self.model = "llama-3.1-8b-instant"

        # if LLM.__shared is None:
        #     logging.info("First LLM() building shared embedder/cross-encoder")
        #     LLM.__shared = {
        #         "embedder": JinaEmbeddings(),
        #         "cross": HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base"),
        #     }

        # shared = LLM.__shared
        self.RAG_instance = RAG_instance if RAG_instance else RAG(env)  # Use provided RAG instance or create a new one
        self.available_functions = {
            "get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            "get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
            "get_deployed_devices_over_time_interval": get_deployed_devices_over_time_interval,
            "get_active_instruments_at_cambridge_bay": get_active_instruments_at_cambridge_bay,
            "generate_download_codes": generate_download_codes,
            "get_daily_air_temperature_stats_cambridge_bay": get_daily_air_temperature_stats_cambridge_bay,
            "get_oxygen_data_24h": get_oxygen_data_24h,
            # "get_ship_noise_acoustic_for_date": get_ship_noise_acoustic_for_date,
            "get_wind_speed_at_timestamp": get_wind_speed_at_timestamp,
            "get_ice_thickness": get_ice_thickness,
        }

    async def run_conversation(
        self, user_prompt, user_onc_token: str, chatHistory: list[dict] = [],  obtainedParams: ObtainedParamsDictionary = {}
    ) -> dict:
        try:
            CurrentDate = datetime.now().strftime("%Y-%m-%d")
            startingPrompt = f"""
                You are a helpful assistant for Ocean Networks Canada that uses tools to answer user queries when needed. 
                Today’s date is {CurrentDate}. You can CHOOSE to use the given tools to obtain the data needed to answer the prompt and provide the results IF that is required.
                Dont summarize data unless asked to.

                You may use tools when required to answer user questions. Do not describe what you *will* do — only use tools if needed.

                When a tool is used, DO NOT continue reasoning or take further steps based on its result.

                Instead, return a final response to the user that clearly and colloquially explains the tool's result — without guessing, adding advice, or planning further steps. Stay within the limits of the message returned by the tool.

                DO NOT speculate or describe what might happen next.

                You are NEVER required to generate code in any language.

                USE the last context of the conversation as the user question to be answered. The previous messages in the conversation are provided to you as context only!
                Do NOT add follow-up suggestions, guesses, or recommendations.

                For data download, do not add properties to the function call unless the user has provided them. 

                DO NOT guess what the tool might return.
                DO NOT say "I will now use the tool".
                DO NOT try to reason about data availability.
                Here is the user_onc_token: {user_onc_token}.
            """


            """
            OTHER POSSIBLE STARTING PROMPT:
                You are a helpful assistant for Ocean Networks Canada that uses tools to answer user queries when needed.  
                Today’s date is {CurrentDate}. You can CHOOSE to use the given tools to obtain the data needed to answer the prompt and provide the results IF that is required.  
                Don't summarize data unless asked to.

                You may use tools when required to answer user questions. Do NOT describe what you *will* do — only use tools if needed.

                When a tool is used, DO NOT continue reasoning or take further steps based on its result.

                Instead, return a final response to the user that clearly and colloquially explains the tool's result — without guessing, adding advice, or planning further steps. Stay within the limits of the message returned by the tool.

                DO NOT speculate or describe what might happen next.

                You are NEVER required to generate code in any language.

                USE the last context of the conversation as the user question to be answered. The previous messages in the conversation are provided to you as context only!  
                Do NOT add follow-up suggestions, guesses, or recommendations.

                For data download requests:  
                - Do NOT add any parameters when calling the data download function.  
                - Your only responsibility is to detect the user’s intent to download data and trigger the data download tool call.  
                - The parameters for the data download function will be determined separately by backend logic using vector database lookups and do NOT require your input.

                DO NOT guess what the tool might return.  
                DO NOT say "I will now use the tool".  
                DO NOT try to reason about data availability.

                Here is the user_onc_token: {user_onc_token}.

                USE the following function description for data download if you use this starting prompt:
                {
                "type": "function",
                    "function": {
                        "name": "generate_download_codes",
                        "description": "Call this function only when the user has expressed an intent to download data from Ocean Networks Canada (ONC). Your sole responsibility is to trigger this tool call; do not provide or guess any parameters. The parameters for this data download function call are obtained separately by backend logic using vector database lookups based on the user's query. Do not attempt to supply or infer deviceCategoryCode, locationCode, dataProductCode, extension, dateFrom, or dateTo. This function will handle missing parameters and generate a response accordingly. After this function is called, you will not be involved in response handling or checking the status of the download. You do not need to explain the result to the user.",
                        "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                        }
                    }
                },
            """
            messages = chatHistory + [
                {
                    "role": "system",
                    "content": startingPrompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
            print("Messages: ", messages)

            vectorDBResponse = self.RAG_instance.get_documents(user_prompt)
            if isinstance(vectorDBResponse, pd.DataFrame):
                if vectorDBResponse.empty:
                    vector_content = ""
                else:
                    # Convert DataFrame to a more readable format
                    vector_content = vectorDBResponse.to_string(index=False)
            else:
                vector_content = str(vectorDBResponse)
            # print("Vector DB Response:", vector_content)
            messages.append({"role": "system", "content": vector_content})

            response = self.client.chat.completions.create(
                model=self.model,  # LLM to use
                messages=messages,  # Conversation history
                stream=False,
                tools=toolDescriptions,  # Available tools (i.e. functions) for our LLM to use
                tool_choice="auto",  # Let our LLM decide when to use tools
                max_completion_tokens=4096,  # Maximum number of tokens to allow in our response
                temperature=0.25,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
            )
            #print("Response from LLM:", response)
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            # print(tool_calls)
            DoingDataDownload = False
            if tool_calls:
                # print("Tool calls detected, processing...")
                print("tools calls:", tool_calls)
                tool_calls = list(OrderedDict(((call.id, call.function.name, call.function.arguments), call) for call in tool_calls).values())
                print("Unique tool calls:", tool_calls)
                for tool_call in tool_calls:
                    # print(tool_call)
                    # print()
                    function_name = tool_call.function.name

                    if function_name in self.available_functions:
                        if function_name == "generate_download_codes":
                            # Special case for download codes
                            print("Generating download codes...")
                            DoingDataDownload = True
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                        print(f"Calling function: {function_name} with args: {function_args}")
                        if (DoingDataDownload):
                            print("function_args: ", function_args)
                            #print("**function_args: ",**function_args)
                            function_args["obtainedParams"] = obtainedParams
                           
                        function_response = await self.call_tool(
                            self.available_functions[function_name],
                            function_args or {},
                            user_onc_token=user_onc_token or self.env.get_onc_token(),
                        )
                        if(DoingDataDownload):
                            if (function_response.get("status") == StatusCode.PARAMS_NEEDED):
                                print("Download parameters needed, returning response now")
                                return RunConversationResponse(
                                        status=StatusCode.PARAMS_NEEDED,
                                        response=function_response.get("response"),
                                        obtainedParams=function_response.get("obtainedParams", {}),
                                )
                            elif (function_response.get("status") == StatusCode.PROCESSING_DATA_DOWNLOAD):
                                print("download done so returning response now")
                                dpRequestId = function_response.get("dpRequestId")
                                doi = function_response.get("doi", "No DOI available")
                                citation = function_response.get("citation", "No citation available")
                                return RunConversationResponse(
                                        status=StatusCode.PROCESSING_DATA_DOWNLOAD,
                                        response=function_response.get("response", "Your download is being processed."),
                                        dpRequestId=dpRequestId,
                                        doi=doi,
                                        citation=citation,
                                    )
                            elif (function_response.get("status") == StatusCode.ERROR_WITH_DATA_DOWNLOAD):
                                print("Download error so returning response now")
                                return RunConversationResponse(
                                        status=StatusCode.ERROR_WITH_DATA_DOWNLOAD,
                                        response=function_response.get("response", "An error occurred while processing your download request."),
                                    )
                            
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",  # Indicates this message is from tool use
                                "name": function_name,
                                "content": json.dumps(function_response),
                            }
                        )  # May be able to use this for getting most recent data if needed.
                # print("Messages after tool calls:", messages)
                second_response = self.client.chat.completions.create(
                    model=self.model, messages=messages, max_completion_tokens=4096, temperature=0.25, stream=False
                )  # Calls LLM again with all the data from all functions
                # Return the final response
                print("Second response: ", second_response.choices[0].message)
                response = second_response.choices[0].message.content
                return RunConversationResponse(
                    status=StatusCode.REGULAR_MESSAGE,
                    response=response
                )
            else:
                print(response_message)
                return RunConversationResponse(
                    status=StatusCode.REGULAR_MESSAGE,
                    response=response_message.content
                )
        except Exception as e:
            logger.error(f"LLM failed: {e}", exc_info=True)
            return RunConversationResponse(
                status=StatusCode.LLM_ERROR,
                response="Sorry, your request failed. Something went wrong with the LLM. Please try again.",
            )

    async def call_tool(self, fn, args, user_onc_token):
        try:
            return await fn(**args, user_onc_token=user_onc_token)
        except TypeError:
            # fallback if fn doesn't accept user_onc_token
            return await fn(**args)


async def main():

    env = Environment()
    RAG_instance = RAG(env)
    print("RAG instance created successfully.")
    try:
        LLM_Instance = LLM(env=env, RAG_instance=RAG_instance)  # Create an instance of the LLM class
        user_prompt = input("Enter your first question (or 'exit' to quit): ")
        chatHistory = []
        obtainedParams = {}
        while user_prompt not in ["exit", "quit"]:
            response = await LLM_Instance.run_conversation(user_prompt=user_prompt, user_onc_token="6a316121-e017-4f4c-9cb1-eaf5dd706425", chatHistory=chatHistory, obtainedParams=obtainedParams)
            print()
            print()
            print()
            print("Response from LLM:", response)
            if (response.status == StatusCode.PROCESSING_DATA_DOWNLOAD):
                print("Download request initiated. Request ID:", response.dpRequestId)
                print("DOI:", response.doi)
                print("Citation:", response.citation)
                obtainedParams = {}
            elif (response.status == StatusCode.PARAMS_NEEDED):
                print("Error:", response.response)
                obtainedParams = response.obtainedParams
                print("Obtained parameters:", obtainedParams)
            else:
                print("Response:", response.response)
            response = {"role": "system", "content": response}
            chatHistory.append({"role": "user", "content": user_prompt})
            user_prompt = input("Enter your next question (or 'exit' to quit): ")

    except Exception as e:
        print("Error occurred:", e)


if __name__ == "__main__":
    asyncio.run(main())
