import json
import logging
import sys
from collections import OrderedDict
from datetime import datetime

import pandas as pd
from langchain.output_parsers import PydanticOutputParser

from LLM.Constants.status_codes import StatusCode
from LLM.Constants.system_prompts import (
    generate_system_prompt,
    system_prompt1,
    system_prompt2,
    system_prompt3,
)
from LLM.Constants.tool_descriptions import toolDescriptions  # , toolDescriptionsShort
from LLM.data_download import generate_download_codes

# from LLM.utils import update_date_to
from LLM.RAG import RAG
from LLM.schemas import (
    ObtainedParamsDictionary,
    PlanningResponse,
    RunConversationResponse,
)
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
parser = PydanticOutputParser(pydantic_object=PlanningResponse)
formatInstructions = parser.get_format_instructions()


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
        user_prompt: str,
        user_onc_token: str,
        chat_history: list[dict] = [],
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary(),
    ) -> RunConversationResponse:
        try:
            CurrentDate = datetime.now().strftime("%Y-%m-%d")
            systemPrompt1 = generate_system_prompt(
                system_prompt1,
                context={
                    "current_date": CurrentDate,
                    "tool_descriptions": json.dumps(toolDescriptions),
                    "format_instructions": formatInstructions,
                },
            )
            messages = [
                {
                    "role": "system",
                    "content": systemPrompt1,
                },
                *chat_history,
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
            response = self.client.chat.completions.create(
                model=self.model,  # LLM to use
                messages=messages,  # Includes Conversation history
                stream=False,
                max_completion_tokens=1024,  # Maximum number of tokens to allow in our response
                temperature=0,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
            )

            # print("Response from LLM:", response.choices[0].message)
            response_message = response.choices[0].message.content
            structured_output = parser.parse(response_message)
            print("Structured Output:", structured_output)
            print()
            print()
            print()
            reasoning = structured_output.reasoning
            inputs_needed = structured_output.inputs_needed
            # print("Reasoning:", reasoning)
            print()
            print()
            print()
            print("Inputs Needed:", inputs_needed)
            VectorDBinput = "User: " + user_prompt + "Assistant: " + str(reasoning)
            vectorDBResponse = self.RAG_instance.get_documents(VectorDBinput)
            print("Vector DB Response:", vectorDBResponse)
            if isinstance(vectorDBResponse, pd.DataFrame):
                if vectorDBResponse.empty:
                    vector_content = ""
                else:
                    # Convert DataFrame to a more readable format
                    # vectorDBResponse['contents'] = vectorDBResponse['contents'].apply(lambda x: update_date_to(x, CurrentDate))
                    vector_content = vectorDBResponse.to_string(index=False)
            else:
                vector_content = str(vectorDBResponse)
            print("Vector DB Response:", vector_content)
            tool_calls = []
            if inputs_needed:
                print("NEED INPUTS")
                systemPrompt2 = generate_system_prompt(
                    system_prompt2,
                    context={
                        "current_date": CurrentDate,
                    },
                )

                messages = [
                    {
                        "role": "system",
                        "content": systemPrompt2,
                    },
                    {
                        "role": "assistant",
                        "content": "inputs needed: " + str(inputs_needed),
                    },
                    {"role": "user", "content": str(reasoning)},
                    {"role": "assistant", "content": vector_content},
                    # {
                    #     "role": "user",
                    #     "content": user_prompt,
                    # },
                ]

                response = self.client.chat.completions.create(
                    model=self.model,  # LLM to use
                    messages=messages,  # Includes Conversation history
                    stream=False,
                    tools=toolDescriptions,  # Available tools (i.e. functions) for our LLM to use
                    tool_choice="auto",  # Let our LLM decide when to use tools
                    max_completion_tokens=512,  # Maximum number of tokens to allow in our response
                    temperature=0,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
                )
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                if response_message.content:
                    print("response_message:", response_message.content)
                print("Tool Calls:", tool_calls)

                # return RunConversationResponse(
                #     status=StatusCode.REGULAR_MESSAGE,
                #     response="",
                # )
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
                            function_args["obtained_params"] = obtained_params

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
                                    function_response.get("obtained_params", {})
                                )
                                print("Obtained parameters:", obtained_params)
                                print("Obtained parameters:", type(obtained_params))
                                # Return a response indicating that Paramaters are needed
                                return RunConversationResponse(
                                    status=StatusCode.PARAMS_NEEDED,
                                    response=function_response.get("response"),
                                    obtained_params=obtained_params,
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
                                obtained_params: ObtainedParamsDictionary = (
                                    function_response.get("obtained_params", {})
                                )
                                # Return a response indicating that there was an error with the download
                                return RunConversationResponse(
                                    status=StatusCode.ERROR_WITH_DATA_DOWNLOAD,
                                    response=function_response.get(
                                        "response",
                                        "An error occurred while processing your download request.",
                                    ),
                                    obtained_params=obtained_params,
                                    urlParamsUsed=function_response.get(
                                        "urlParamsUsed", {}
                                    ),
                                    baseUrl=function_response.get(
                                        "baseUrl",
                                        "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
                                    ),
                                )
                        else:
                            # Not doing data download so clearing the obtained_params
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
            systemPrompt3 = generate_system_prompt(
                system_prompt3,
                context={
                    "current_date": CurrentDate,
                },
            )
            messagesNoContext = [
                {
                    "role": "system",
                    "content": systemPrompt3,
                },
                {"role": "assistant", "content": vector_content},
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
            if tool_calls:
                messagesNoContext.extend(
                    toolMessages
                )  # Add tool messages to the conversation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messagesNoContext,  # Conversation history without context and different starting system prompt
                max_completion_tokens=4096,
                temperature=0,
                stream=False,
            )  # Calls LLM again with all the data from all functions
            # Return the final response
            print("final response: ", response.choices[0].message)
            response = response.choices[0].message.content
            if tool_calls:
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
                    status=StatusCode.REGULAR_MESSAGE, response=response
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
