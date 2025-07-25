import json
import logging
import sys
from collections import OrderedDict
from datetime import datetime

import pandas as pd

from LLM.Constants.status_codes import StatusCode
from LLM.Constants.tool_descriptions import toolDescriptions
from LLM.data_download import generate_download_codes
from LLM.general_data import get_scalar_data
from LLM.RAG import RAG
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse
from LLM.tools_sprint1 import (
    get_active_instruments_at_cambridge_bay,
    get_daily_sea_temperature_stats_cambridge_bay,
    get_deployed_devices_over_time_interval,
    get_time_range_of_available_data,
    # get_properties_at_cambridge_bay,
)
from LLM.tools_sprint2 import (
    get_daily_air_temperature_stats_cambridge_bay,
    get_ice_thickness,
    get_oxygen_data_24h,
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
            # "get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            "get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
            "get_deployed_devices_over_time_interval": get_deployed_devices_over_time_interval,
            "get_active_instruments_at_cambridge_bay": get_active_instruments_at_cambridge_bay,
            "generate_download_codes": generate_download_codes,
            "get_daily_air_temperature_stats_cambridge_bay": get_daily_air_temperature_stats_cambridge_bay,
            "get_oxygen_data_24h": get_oxygen_data_24h,
            "get_wind_speed_at_timestamp": get_wind_speed_at_timestamp,
            "get_ice_thickness": get_ice_thickness,
            "get_scalar_data": get_scalar_data,
            "get_time_range_of_available_data": get_time_range_of_available_data,
        }

    async def run_conversation(
        self,
        user_prompt: str,
        user_onc_token: str,
        chat_history: list[dict] = [],
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary(),
    ) -> RunConversationResponse:
        try:
            CurrentDate = datetime.now().strftime("%Y-%m-%d")
            startingPrompt = f"""
                You are a helpful assistant for Ocean Networks Canada. You may use tools to answer the user’s question only when strictly necessary.

                Today’s date is {CurrentDate}. You may use the provided tools if needed to retrieve data required to answer the user's question.

                Prioritize the most recent user input!

                Only use a tool when **all** of the following conditions are true:
                - The user has explicitly asked to retrieve or download data, or has requested time-series measurements over a time range.
                - AND the user has not already received a successful answer to this request in a previous assistant message.
                - AND the answer is not already available from vector search results or prior assistant responses.

                You MUST NOT use any tool:
                - If the user only mentions device, location, or parameter information without asking to download or retrieve values.
                - If the user says "thank you", "goodbye", or anything similar.
                - If the question is conceptual, relates to sensor metadata, or is not about obtaining data.
                - If the user has not clearly asked for specific data.
                
                When asked about the temperature, clarify with the user if they want air or sea temperature data, as they are different measurements.
                
                If a user requests scalar data then use the `get_scalar_data` tool to retrieve it. DO NOT use the `generate_download_codes` tool for scalar data requests. 
                DO NOT use the `get_scalar_data` tool if the user does not request scalar data.

                When tool usage is appropriate:
                - NEVER guess or infer missing parameters.
                - Use only the exact values provided by the user for `dateFrom`, `dateTo`, etc. If not provided, leave them blank.
                - Do NOT set `dpo_resample` unless explicitly described by the user.
                - Always include the exact date range used in the query in your final response.
                - If `dateFrom` and `dateTo` are the same, say the data was "sampled on that day" instead of referring to a date range.
                - NEVER infer or assume what the extension should be for a download request.
                - Only use values from the allowed enums when calling tools. Do not make up or guess values.

                Only set `dpo_resample` when:
                - The user has explicitly requested to retrieve or download data.
                - AND the user clearly specifies how the data should be summarized:
                - If they mention “average”, “averages per minute”, or “mean values” → set `dpo_resample` to `"average"`.
                - If they mention “min and max”, “extremes”, or “range values” → set `dpo_resample` to `"minMax"`.
                - If they request all three (min, max, and average) → set `dpo_resample` to `"minMaxAvg"`.

                Do NOT set `dpo_resample`:
                - If the user is not explicitly requesting data.
                - If their summary request is vague or ambiguous.
                - If you are not using a data download tool.

                Always end your response with a warm, friendly closing, such as:
                “Let me know if you have any other questions!”
            """
            # If the user requests an example of data without specifying the `dateFrom` or `dateTo` parameters, use the most recent available dates for the requested device.

            # print("Messages: ", messages)
            sources = []
            vectorDBResponse = self.RAG_instance.get_documents(user_prompt)
            print("Vector DB Response:", vectorDBResponse)

            if isinstance(vectorDBResponse, pd.DataFrame):
                if vectorDBResponse.empty:
                    vector_content = ""
                else:
                    if "sources" in vectorDBResponse.columns:
                        # we need a list of sources to return with the LLM response
                        sources = vectorDBResponse["sources"].tolist()
                    # Convert DataFrame to a more readable format
                    vector_content = vectorDBResponse.to_string(index=False)
            else:
                vector_content = str(vectorDBResponse)
            print("Vector DB Response:", vector_content)
            messages = [
                {
                    "role": "system",
                    "content": startingPrompt,
                },
                *chat_history,
                {
                    "role": "user",
                    "content": f"(Sensor Information from Vector Search for context only):\n{vector_content}",
                },
                {
                    "role": "user",
                    "content": f"Using the above information as context answer the following: {user_prompt}",
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
            doing_scalar_request = False
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
                        if function_name == "get_scalar_data":
                            print("Doing Scalar request...")
                            doing_scalar_request = True
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                        print(
                            f"Calling function: {function_name} with args: {function_args}"
                        )
                        if doing_data_download or doing_scalar_request:
                            print("function_args: ", function_args)
                            # print("**function_args: ",**function_args)
                            function_args["obtainedParams"] = obtained_params

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
                                obtained_params: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                print("Obtained parameters:", obtained_params)
                                print("Obtained parameters:", type(obtained_params))
                                # Return a response indicating that Paramaters are needed
                                return RunConversationResponse(
                                    status=StatusCode.PARAMS_NEEDED,
                                    response=function_response.get("response"),
                                    obtainedParams=obtained_params,
                                    sources=sources,
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
                                obtained_params: ObtainedParamsDictionary = (
                                    ObtainedParamsDictionary()
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
                                    obtainedParams=obtained_params,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
                                    ),
                                    sources=sources,
                                )
                            elif (
                                DataDownloadStatus
                                == StatusCode.ERROR_WITH_DATA_DOWNLOAD
                            ):
                                print("Download error so returning response now")
                                obtained_params: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                # Return a response indicating that there was an error with the download
                                return RunConversationResponse(
                                    status=StatusCode.ERROR_WITH_DATA_DOWNLOAD,
                                    response=function_response.get(
                                        "response",
                                        "An error occurred while processing your download request.",
                                    ),
                                    obtainedParams=obtained_params,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
                                    ),
                                    sources=sources,
                                )
                        elif doing_scalar_request:
                            scalarRequestStatus = function_response.get("status")
                            if scalarRequestStatus == StatusCode.PARAMS_NEEDED:
                                print(
                                    "Scalar request parameters needed, returning response now"
                                )
                                obtained_params: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                # Return a response indicating that Paramaters are needed
                                return RunConversationResponse(
                                    status=StatusCode.PARAMS_NEEDED,
                                    response=function_response.get("response"),
                                    obtainedParams=obtained_params,
                                    sources=sources,
                                )
                            elif scalarRequestStatus == StatusCode.DEPLOYMENT_ERROR:
                                print(
                                    "Scalar request parameters needed, returning response now"
                                )
                                obtained_params: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                print(function_response.get("result"))
                                # Return a response indicating that Paramaters are needed
                                return RunConversationResponse(
                                    status=StatusCode.DEPLOYMENT_ERROR,
                                    response=function_response.get("response"),
                                    obtainedParams=obtained_params,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/scalardata/location",
                                    ),
                                    sources=sources,
                                )
                            elif scalarRequestStatus == StatusCode.NO_DATA:
                                print("No data returned.")
                                obtained_params: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                print("Obtained parameters:", obtained_params)
                                print("Obtained parameters:", type(obtained_params))
                                # Return a response indicating that Paramaters are needed
                                return RunConversationResponse(
                                    status=StatusCode.DEPLOYMENT_ERROR,
                                    response=function_response.get("description"),
                                    obtainedParams=obtained_params,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/scalardata/location",
                                    ),
                                    sources=sources,
                                )
                            elif scalarRequestStatus == StatusCode.SCALAR_REQUEST_ERROR:
                                print("No data returned.")
                                obtained_params: ObtainedParamsDictionary = (
                                    function_response.get("obtainedParams", {})
                                )
                                print("Obtained parameters:", obtained_params)
                                print("Obtained parameters:", type(obtained_params))
                                # Return a response indicating that Paramaters are needed
                                return RunConversationResponse(
                                    status=StatusCode.SCALAR_REQUEST_ERROR,
                                    response=function_response.get("response"),
                                    obtainedParams=obtained_params,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/scalardata/location",
                                    ),
                                    sources=sources,
                                )
                        # Not doing data download or scalar request is successful so clearing the obtainedParams
                        obtained_params: ObtainedParamsDictionary = (
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

                    DO NOT say "Here is you data in a table format:"

                    If minimum/maximum/average is in the tool response, YOU MUST format it this way. DO NOT include any other tables of data. Make sure the columns are lined up. Minimum/Maximum/Average data must be formatted in the following format:

                    | Measurement               | Time                      | [Measurement Name] (units) |
                    |---------------------------|---------------------------|----------------------------|
                    |    Minimum                |    YYYY-MM-DD HH:MM:SS    | [min]                      |
                    |    Maximum                |    YYYY-MM-DD HH:MM:SS    | [max]                      |
                    |    Average                |                           | [average]                  |

                    Only include the most relevant columns (usually no more than 2–4). If the result is long, truncate it to the first 24 rows and note that more data is available. Do not summarize or interpret the table unless the user asks.
                    
                    IF you get results from two or more tools, you MUST display or combine the results into a single response. For example: if you get air and sea stats then display both if the user didnt just ask for one or the other.

                    Convert Time fields to the following format: `YYYY-MM-DD HH:MM:SS` (e.g., from `2023-10-01T12:00:00.000Z` To `2023-10-01 12:00:00` ).
                    
                    You must not speculate, infer unavailable values, or offer additional analysis unless explicitly asked.

                    Do not summarize or interpret data unless explicitly asked.

                    If the user asks whether a type of data or measurement is available at a given observatory or location, respond with a simple yes or no based on the given message context.

                    After every answer you give—no matter what the topic is—you MUST end your response with a warm, natural follow-up like:
                    “Is there anything else I can help you with?” or “Let me know if you have any other questions!”

                    This closing line is required even if the user just says “thanks” or ends the conversation.

                    If the user says something like “thanks” or “goodbye”, you should still respond with a friendly closing line like:
                    “You’re welcome! If you have any more questions in the future, feel free to ask. Have a great day!” or “Goodbye! If you need anything else, just let me know!”

                    When a tool is used, do not guess or assume what it might return. Do not speculate or reason beyond the returned result. However, you may output the tool’s result in your response and format it clearly for the user, as long as you do not add new interpretations or steps.

                    You MUST explicitly include the name “Cambridge Bay” in your response whenever tool results are based on data from that location. Do not use vague phrases like “the Arctic” or “polar regions.” You must also clearly state the date range used in the tool query (e.g., dateFrom and dateTo). If the dateFrom and dateTo values fall on the same day, say that the data was sampled on that day rather than referring to a date range.

                    You are NEVER required to generate code in any language.

                    NEVER use a dateFrom or dateTo value that is in the future.

                    Do NOT add follow-up suggestions, guesses, or recommendations.

                    DO NOT guess what parameters the user might want to use for data download requests.

                    DO NOT say "I will now use the tool."  
                    DO NOT try to reason about data availability.

                    DO NOT MAKE UP DATA. Only use data returned from the tools.
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
                        "content": user_prompt,
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
                    obtainedParams=obtained_params,
                    urlParamsUsed=function_response.get("urlParamsUsed", {}),
                    baseUrl=function_response.get(
                        "baseUrl",
                        "",
                    ),
                    sources=sources,
                )
            else:
                print(response_message)
                return RunConversationResponse(
                    status=StatusCode.REGULAR_MESSAGE,
                    response=response_message.content,
                    sources=sources,
                    obtainedParams=obtained_params,
                )
        except Exception as e:
            logger.error(f"LLM failed: {e}", exc_info=True)
            return RunConversationResponse(
                status=StatusCode.LLM_ERROR,
                response="Sorry, your request failed. Something went wrong with the LLM. Please try again.",
                obtainedParams=obtained_params,
                sources=sources,
            )

    async def call_tool(self, fn, args, user_onc_token):
        try:
            return await fn(**args, user_onc_token=user_onc_token)
        except TypeError:
            # fallback if fn doesn't accept user_onc_token
            return await fn(**args)
