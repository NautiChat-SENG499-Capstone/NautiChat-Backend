import json
import logging
import sys
from collections import OrderedDict
from datetime import datetime

import pandas as pd

from LLM.Constants.status_codes import StatusCode
from LLM.Constants.system_prompts import (
    first_LLM_prompt,
    generate_system_prompt,
    second_LLM_prompt,
)
from LLM.Constants.tool_descriptions import toolDescriptions
from LLM.Constants.utils import handle_data_download, handle_scalar_request
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
            current_date = datetime.now().strftime("%Y-%m-%d")
            startingPrompt = generate_system_prompt(
                first_LLM_prompt,
                context={
                    "current_date": current_date,
                },
            )
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
            # print("Vector DB Response:", vector_content)

            qa_docs = self.RAG_instance.get_qa_docs(user_prompt)

            if isinstance(qa_docs, pd.DataFrame):
                if qa_docs.empty:
                    qa_reference = "" 
                else:
                    qa_reference = qa_docs.to_string(index=False)
            else:
                qa_reference = str(qa_docs)

            messages = [
                {
                    "role": "system",
                    "content": startingPrompt,
                }
            ]
            if qa_reference:
                styling_prompt = f"""
                The following are examples of question-answer pairs that represent the desired style, tone, and preferred phrasing for your responses.
                These examples are **CRUCIALLY ONLY for stylistic guidance** and do **NOT** represent current factual information, data availability, tool usage, or required parameters.
                You **MUST NOT** use these examples as factual context or directly answer from them.
                Instead, analyze them **solely** to understand the preferred phrasing, level of detail, and overall stylistic conventions
                when formulating your own answers based on other retrieved information and tool outputs.
                **Absolutely DO NOT** initiate any tool calls based on the content or patterns found within these styling examples.

                Examples for styling guidance:
                {qa_reference}
                """
                messages.append({"role": "system", "content": styling_prompt})

            messages.extend([
                {"role": "assistant", "content": vector_content},
                *chat_history,
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ])

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
                            function_args["obtainedParams"] = obtained_params

                        function_response = await self.call_tool(
                            self.available_functions[function_name],
                            function_args or {},
                            user_onc_token=user_onc_token or self.env.get_onc_token(),
                        )
                        print("Function response:", function_response)
                        if doing_data_download:
                            return handle_data_download(function_response, sources)
                        elif doing_scalar_request:
                            scalarRequestStatus = function_response.get("status")
                            if scalarRequestStatus != StatusCode.REGULAR_MESSAGE:
                                return handle_scalar_request(
                                    function_response, sources, scalarRequestStatus
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
                secondLLMCallStartingPrompt = generate_system_prompt(
                    second_LLM_prompt,
                    context={
                        "current_date": current_date,
                    },
                )
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
