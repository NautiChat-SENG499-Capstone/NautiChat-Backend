import json
import logging
import sys
from collections import OrderedDict
from datetime import datetime

import pandas as pd
from groq import APIStatusError, RateLimitError

from LLM.Constants.status_codes import StatusCode
from LLM.Constants.tool_descriptions import toolDescriptions
from LLM.data_download import generate_download_codes
from LLM.RAG import RAG
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse
from LLM.tools_sprint1 import (
    get_active_instruments_at_cambridge_bay,
    # get_time_range_of_available_data,
    get_daily_sea_temperature_stats_cambridge_bay,
    get_deployed_devices_over_time_interval,
    get_properties_at_cambridge_bay,
)
from LLM.tools_sprint2 import (
    get_daily_air_temperature_stats_cambridge_bay,
    get_ice_thickness,
    get_oxygen_data_24h,
    # get_ship_noise_acoustic_for_date,
    get_wind_speed_at_timestamp,
)

logger = logging.getLogger(__name__)

sys.modules["LLM"] = sys.modules[__name__]


class LLM:
    def __init__(self, env, *, RAG_instance=None):
        self.env = env
        self.client = env.get_client()
        self.model = env.get_model()
        self.RAG_instance: RAG = RAG_instance or RAG(env=self.env)
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
        self,
        userPrompt: str,
        user_onc_token: str,
        chatHistory: list[dict] = [],
        obtainedParams: ObtainedParamsDictionary = ObtainedParamsDictionary(),
        hasRetriedConversation: bool = False,
    ) -> RunConversationResponse:
        try:
            CurrentDate = datetime.now().strftime("%Y-%m-%d")
            startingPrompt = f"""
                You are a helpful assistant for Ocean Networks Canada that uses tools to answer user queries when needed.

                Today’s date is {CurrentDate}. You can CHOOSE to use the given tools to obtain the data needed to answer the prompt and provide the results IF that is required.

                You MUST prioritize information provided to you via previous assistant messages (such as search results or sensor descriptions) before using any tools.

                You should ONLY use the data download tool/generate_download_codes tool or any other time-series-related tool when the user:
                - explicitly asks to download or retrieve data,
                - requests measurements, time series, plots, or values over a date or time range,
                - or provides specific parameters like `dateFrom`, `dateTo`, or timestamp values.

                Do NOT use the data download tool/generate_download_codes tool if the user does not request to download data.

                IGNORE messaging history about downloading data when the user is not explicitly asking to download data and the previous data download was successful.

                Even if valid parameters (such as `deviceCategoryCode`, `dataProductCode`, or `locationCode`) are present in the conversation or from the vector search, do NOT assume the user wants data. The presence of these parameters is common and should be treated as context only.

                Do NOT use any data-fetching tools for general, conceptual, or sensor-related questions if relevant information has already been provided (e.g., from a vector search or assistant message).

                When the user describes how the data should be summarized:
                - If they say "average", "averages per minute", "mean values", or similar, set `dpo_resample` to `"average"`.
                - If they say "min and max", "extremes", or "range values", set `dpo_resample` to `"minMax"`.
                - If they say "min, max, and average", or ask for all three statistics per interval, set `dpo_resample` to `"minMaxAvg"`.

                Do not guess. Only set `dpo_resample` if the user's language clearly matches one of these resampling strategies. Otherwise, omit it or use "none".

                Listing or describing sensors is enough to answer most conceptual questions — you should NOT follow up by trying to download or offer data unless the user has clearly asked for it.

                If the user wants an example of data, you should return the data retrieved from the relevant tools or APIs.

                Convert Time fields to the following format: `YYYY-MM-DD HH:MM:SS` (e.g., from `2023-10-01T12:00:00.000Z` To `2023-10-01 12:00:00` ).
                
                You must not speculate, infer unavailable values, or offer additional analysis unless explicitly asked.

                Do not summarize or interpret data unless explicitly asked.

                If the user asks whether a type of data or measurement is available at a given observatory or location, respond with a simple yes or no based on your knowledge of the vector search information. Do NOT call data retrieval functions in response to such questions.

                After every answer you give—no matter what the topic is—you MUST end your response with a warm, natural follow-up like:
                “Is there anything else I can help you with?” or “Let me know if you have any other questions!”

                This closing line is required even if the user just says “thanks” or ends the conversation.

                If the user says something like “thanks” or “goodbye”, you should still respond with a friendly closing line like:
                “You’re welcome! If you have any more questions in the future, feel free to ask. Have a great day!” or “Goodbye! If you need anything else, just let me know!”

                You may use tools when required to answer user questions. Do not describe what you *will* do — only use tools if needed.

                When a tool is used, do not guess or assume what it might return. Do not speculate or reason beyond the returned result. However, you may output the tool’s result in your response and format it clearly for the user, as long as you do not add new interpretations or steps.

                You are NEVER required to generate code in any language.

                Do NOT add follow-up suggestions, guesses, or recommendations.

                DO NOT guess what parameters the user might want to use for data download requests.

                DO NOT guess what the tool might return.  
                DO NOT say "I will now use the tool."  
                DO NOT try to reason about data availability.

                If the user requests an example of data without specifying the `dateFrom` or `dateTo` parameters, use the most recent available dates for the requested device.
            """

            # print("Messages: ", messages)

            vectorDBResponse = self.RAG_instance.get_documents(userPrompt)
            print("Vector DB Response:", vectorDBResponse)
            if isinstance(vectorDBResponse, pd.DataFrame):
                if vectorDBResponse.empty:
                    vector_content = ""
                else:
                    # Convert DataFrame to a more readable format
                    vector_content = vectorDBResponse.to_string(index=False)
            else:
                vector_content = str(vectorDBResponse)
            # print("Vector DB Response:", vector_content)
            messages = [
                {
                    "role": "system",
                    "content": startingPrompt,
                },
                {"role": "assistant", "content": vector_content},
                *chatHistory,
                {
                    "role": "user",
                    "content": userPrompt,
                },
            ]

            response = self.client.chat.completions.create(
                model=self.model,  # LLM to use
                messages=messages,  # Includes Conversation history
                stream=False,
                tools=toolDescriptions,  # Available tools (i.e. functions) for our LLM to use
                tool_choice="auto",  # Let our LLM decide when to use tools
                max_completion_tokens=4096,  # Maximum number of tokens to allow in our response
                temperature=0,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            print("First Response from LLM:", response_message.content)
            # print(tool_calls)
            doing_data_download = False
            if tool_calls:
                # print("Tool calls detected, processing...")
                # print("tools calls:", tool_calls)
                tool_calls = list(
                    OrderedDict(
                        ((call.id, call.function.name, call.function.arguments), call)
                        for call in tool_calls
                    ).values()
                )
                print("Unique tool calls:", tool_calls)
                toolMessages = []
                for tool_call in tool_calls:
                    # print(tool_call)
                    # print()
                    function_name = tool_call.function.name

                    if function_name in self.available_functions:
                        if function_name == "generate_download_codes":
                            # Special case for download codes
                            print("Generating download codes...")
                            doing_data_download = True
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                        print(
                            f"Calling function: {function_name} with args: {function_args}"
                        )
                        if doing_data_download:
                            print("function_args: ", function_args)
                            # print("**function_args: ",**function_args)
                            function_args["obtainedParams"] = obtainedParams

                        function_response = await self.call_tool(
                            self.available_functions[function_name],
                            function_args or {},
                            user_onc_token=user_onc_token or self.env.get_onc_token(),
                        )
                        print("Function response:", function_response)
                        if doing_data_download:
                            DataDownloadStatus = function_response.get("status")
                            if DataDownloadStatus == StatusCode.PARAMS_NEEDED:
                                print(
                                    "Download parameters needed, returning response now"
                                )
                                obtainedParams: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                print("Obtained parameters:", obtainedParams)
                                print("Obtained parameters:", type(obtainedParams))
                                # Return a response indicating that Paramaters are needed
                                return RunConversationResponse(
                                    status=StatusCode.PARAMS_NEEDED,
                                    response=function_response.get("response"),
                                    obtainedParams=obtainedParams,
                                )
                            elif (
                                DataDownloadStatus
                                == StatusCode.PROCESSING_DATA_DOWNLOAD
                            ):
                                print("download done so returning response now")
                                dpRequestId = function_response.get("dpRequestId")
                                doi = function_response.get("doi", "No DOI available")
                                citation = function_response.get(
                                    "citation", "No citation available"
                                )
                                # Return a response indicating that the download is being processed
                                return RunConversationResponse(
                                    status=StatusCode.PROCESSING_DATA_DOWNLOAD,
                                    response=function_response.get(
                                        "response", "Your download is being processed."
                                    ),
                                    dpRequestId=dpRequestId,
                                    doi=doi,
                                    citation=citation,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
                                    ),
                                )
                            elif (
                                DataDownloadStatus
                                == StatusCode.ERROR_WITH_DATA_DOWNLOAD
                            ):
                                print("Download error so returning response now")
                                obtainedParams: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                # Return a response indicating that there was an error with the download
                                return RunConversationResponse(
                                    status=StatusCode.ERROR_WITH_DATA_DOWNLOAD,
                                    response=function_response.get(
                                        "response",
                                        "An error occurred while processing your download request.",
                                    ),
                                    obtainedParams=obtainedParams,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
                                    ),
                                )
                        else:
                            # Not doing data download so clearing the obtainedParams
                            obtainedParams: ObtainedParamsDictionary = (
                                ObtainedParamsDictionary()
                            )

                        toolMessages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",  # Indicates this message is from tool use
                                "name": function_name,
                                "content": json.dumps(
                                    function_response.get("response", "")
                                ),
                            }
                        )  # May be able to use this for getting most recent data if needed.
                # print("Messages after tool calls:", messages)
                secondLLMCallStartingPrompt = f"""
                    You are a helpful assistant for Ocean Networks Canada that uses tools to answer user queries when needed.

                    Today’s date is {CurrentDate}. GIVEN the tools responses create a valuable response based on the users input.

                    Do NOT use any data-fetching tools for general, conceptual, or sensor-related questions if relevant information has already been provided (e.g., from a vector search or assistant message).

                    ALWAYS tell the user what the data is about, what it represents, and how to interpret it.

                    ALWAYS When responding, begin by restating or summarizing the user's request in your own words before providing the answer.

                    You may include the tool result in your reply, formatted clearly and conversationally. Time series or tabular data MUST be rendered as a markdown table with headers, where each row corresponds to one time point and each column corresponds to a variable. Use readable formatting — for example:


                    | Time                      | [Measurement Name] (units) |
                    |---------------------------|----------------------------|
                    |    YYYY-MM-DD HH:MM:SS    | [value1]                   |
                    |    YYYY-MM-DD HH:MM:SS    | [value2]                   |

                    Only include the most relevant columns (usually no more than 2–4). If the result is long, truncate it to the first 24 rows and note that more data is available. Do not summarize or interpret the table unless the user asks.

                    IF you get results from two or more tools, you MUST display or combine the results into a single response. For example: if you get air and sea stats then display both if the user didnt just ask for one or the other.

                    Convert Time fields to the following format: `YYYY-MM-DD HH:MM:SS` (e.g., from `2023-10-01T12:00:00.000Z` To `2023-10-01 12:00:00` ).

                    IF you get results from two or more tools, you MUST display or combine the results into a single response. For example: if you get air and sea stats then display both if the user didnt just ask for one or the other.
                    
                    You must not speculate, infer unavailable values, or offer additional analysis unless explicitly asked.

                    Do not summarize or interpret data unless explicitly asked.

                    If the user asks whether a type of data or measurement is available at a given observatory or location, respond with a simple yes or no based on the given message context.

                    After every answer you give—no matter what the topic is—you MUST end your response with a warm, natural follow-up like:
                    “Is there anything else I can help you with?” or “Let me know if you have any other questions!”

                    This closing line is required even if the user just says “thanks” or ends the conversation.

                    If the user says something like “thanks” or “goodbye”, you should still respond with a friendly closing line like:
                    “You’re welcome! If you have any more questions in the future, feel free to ask. Have a great day!” or “Goodbye! If you need anything else, just let me know!”

                    When a tool is used, do not guess or assume what it might return. Do not speculate or reason beyond the returned result. However, you may output the tool’s result in your response and format it clearly for the user, as long as you do not add new interpretations or steps.

                    You are NEVER required to generate code in any language.

                    Do NOT add follow-up suggestions, guesses, or recommendations.

                    DO NOT guess what parameters the user might want to use for data download requests.

                    DO NOT say "I will now use the tool."  
                    DO NOT try to reason about data availability.
                """
                messagesNoContext = [
                    {
                        "role": "system",
                        "content": secondLLMCallStartingPrompt,
                    },
                    {"role": "assistant", "content": vector_content},
                    *toolMessages,  # Add tool messages to the conversation
                    {
                        "role": "user",
                        "content": userPrompt,
                    },
                ]
                second_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messagesNoContext,  # Conversation history without context and different starting system prompt
                    max_completion_tokens=4096,
                    temperature=0,
                    stream=False,
                )  # Calls LLM again with all the data from all functions
                # Return the final response
                print("Second response: ", second_response.choices[0].message)
                response = second_response.choices[0].message.content
                return RunConversationResponse(
                    status=StatusCode.REGULAR_MESSAGE,
                    response=response,
                    urlParamsUsed=function_response.get("urlParamsUsed", {}),
                    baseUrl=function_response.get(
                        "baseUrl",
                        "",
                    ),
                )
            else:
                print(response_message)
                return RunConversationResponse(
                    status=StatusCode.REGULAR_MESSAGE, response=response_message.content
                )
        except Exception as e:
            logger.info(f"LLM failed on first attempt: {e}", exc_info=True)

            # check if the error was a groq API limit and we have not retried the conversation already
            if isinstance(e, APIStatusError) and not hasRetriedConversation:
                try:
                    self.env.cycle_new_groq_api_key()
                    logger.info("Cycled tokens, retrying run_conversation once.")
                    return await self.run_conversation(
                        userPrompt,
                        chatHistory=chatHistory,
                        user_onc_token=user_onc_token,
                        hasRetriedConversation=True,
                    )
                except Exception as retry_error:
                    logger.error(
                        f"Retry after cycling tokens failed: {retry_error}",
                        exc_info=True,
                    )
                    return RunConversationResponse(
                        status=StatusCode.LLM_ERROR,
                        response="Sorry, your request failed. Something went wrong with the LLM. Please try again.",
                    )

            # LLM failed for reasons unrelated to token limits or conversation was run twice

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
