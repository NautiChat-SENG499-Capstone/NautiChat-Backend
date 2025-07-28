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
from LLM.Constants.utils import (
    create_user_call,
    handle_data_download,
    handle_scalar_request,
)
from LLM.data_download import generate_download_codes
from LLM.general_data import get_scalar_data
from LLM.RAG import RAG
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse, ToolCall
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

    async def get_vectorDB_content(
        self, user_prompt: str, previous_vdb_ids: list[str] = []
    ):
        (vectorDBResponse, point_ids) = self.RAG_instance.get_documents(
            user_prompt, previous_vdb_ids
        )
        print("Vector DB Response:", vectorDBResponse)
        sources = []
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
        print("FULL Vector DB Response:", vector_content)

        return sources, point_ids, vector_content

    async def run_conversation(
        self,
        user_prompt: str,
        user_onc_token: str,
        chat_history: list[dict] = [],
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary(),
        previous_vdb_ids: list[str] = [],
    ) -> RunConversationResponse:
        point_ids = None
        sources = None
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            startingPrompt = generate_system_prompt(
                first_LLM_prompt,
                context={
                    "current_date": current_date,
                },
            )
            # If the user requests an example of data without specifying the `dateFrom` or `dateTo` parameters, use the most recent available dates for the requested device.

            sources, point_ids, vector_content = await self.get_vectorDB_content(
                user_prompt, previous_vdb_ids=previous_vdb_ids
            )

            if (
                len(chat_history) > 0
            ):  # if its not the first message in the conversation
                # Check if the new user prompt is related to the previous conversation. If its not then remove conversation history. If it is then keep the conversation history.
                contextPrompt = f"""User’s new question: {user_prompt}
                    Previous conversation snippet: {chat_history}

                    Is this new question related to previous conversation? Answer yes or no.
                    Note: it is not related if the previous conversation was about a different device or data product.
                """
                messages = [{"role": "system", "content": contextPrompt}]
                keepContext = self.client.chat.completions.create(
                    model=self.model,  # LLM to use
                    messages=messages,  # Includes Conversation history
                    stream=False,
                    max_completion_tokens=1,  # Maximum number of tokens to allow in our response
                    temperature=0,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
                )
                print("Keep context response:", keepContext.choices[0].message.content)
                if keepContext.choices[0].message.content.lower() == "no":
                    chat_history = []

            # qa_docs = self.RAG_instance.get_qa_docs(user_prompt)

            # if isinstance(qa_docs, pd.DataFrame):
            #     if qa_docs.empty:
            #         qa_reference = ""
            #     else:
            #         qa_reference = qa_docs.to_string(index=False)
            # else:
            #     qa_reference = str(qa_docs)
            # styling_prompt = ""

            # if qa_reference:
            #     styling_prompt = f"""
            #     The following responses are ONLY used for styling and tone references.
            #     DO NOT use the information and data in these responses to generate your own responses.
            #     Examples for styling guidance:
            #     {qa_reference}
            #     """

            messages = [
                # {
                #     "role": "system",
                #     "content": styling_prompt,
                # },
                {
                    "role": "system",
                    "content": startingPrompt,
                },
                *chat_history,
                {
                    "role": "user",
                    "content": create_user_call(
                        user_prompt=user_prompt, vector_content=vector_content
                    ),
                },
            ]
            # print("Messages before tool calls:", messages)

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
            # print("First Response from LLM:", response_message.content)
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
                    # print()
                    function_name = tool_call.function.name

                    if function_name in self.available_functions:
                        if function_name == "generate_download_codes":
                            # Special case for download codes
                            # print("Generating download codes...")
                            doing_data_download = True
                        if function_name == "get_scalar_data":
                            # print("Doing Scalar request...")
                            doing_scalar_request = True
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                        print(
                            f"Calling function: {function_name} with args: {function_args}"
                        )
                        function_args_no_obtained_params = (
                            function_args.copy() if function_args else {}
                        )
                        if doing_data_download or doing_scalar_request:
                            # print("function_args: ", function_args)
                            # print("**function_args: ",**function_args)
                            function_args["obtainedParams"] = obtained_params

                        function_response = await self.call_tool(
                            self.available_functions[function_name],
                            function_args or {},
                            user_onc_token=user_onc_token or self.env.get_onc_token(),
                        )
                        print("Function response:", function_response)
                        if doing_data_download:
                            return handle_data_download(
                                function_response, sources, point_ids=point_ids
                            )
                        elif doing_scalar_request:
                            scalarRequestStatus = function_response.get("status")
                            if scalarRequestStatus != StatusCode.REGULAR_MESSAGE:
                                return handle_scalar_request(
                                    function_response,
                                    sources,
                                    scalarRequestStatus,
                                    point_ids=point_ids,
                                )
                        # Not doing data download or scalar request is successful so clearing the obtainedParams
                        obtained_params: ObtainedParamsDictionary = (
                            ObtainedParamsDictionary()
                        )

                        toolMessages.append(
                            ToolCall(
                                function_name=function_name,
                                arguments=json.dumps(
                                    function_args_no_obtained_params
                                ),  # maybe try with and without obtainedParams to see if better or worse
                                response=json.dumps(
                                    function_response.get("response", "")
                                ),
                            )
                        )
                        # toolMessages.append(
                        #     {
                        #         "role": "assistant",
                        #         "tool_call": {
                        #             "name": function_name,
                        #             "arguments": function_args_no_obtained_params,
                        #         }
                        #     }
                        # )
                        # toolMessages.append(
                        #     {
                        #         "role": "tool",  # Indicates this message is from tool use
                        #         "name": function_name,
                        #         "content": json.dumps(
                        #             function_response.get("response", "")
                        #         ),
                        #     }
                        # )  # May be able to use this for getting most recent data if needed.
                # print("Messages after tool calls:", messages)
                secondLLMCallStartingPrompt = generate_system_prompt(
                    second_LLM_prompt,
                    context={
                        "current_date": current_date,
                    },
                )

                userInput = create_user_call(
                    user_prompt=user_prompt,
                    vector_content=vector_content,
                    toolInfo=toolMessages,
                )
                messagesNoContext = [
                    # {"role": "system", "content": styling_prompt},
                    {
                        "role": "system",
                        "content": secondLLMCallStartingPrompt,
                    },
                    {"role": "user", "content": userInput},
                ]
                # print("Messages without context:", messagesNoContext)
                second_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messagesNoContext,  # Conversation history without context and different starting system prompt
                    max_completion_tokens=4096,
                    temperature=0,
                    stream=False,
                )  # Calls LLM again with all the data from all functions
                # Return the final response
                # print("Second response: ", second_response.choices[0].message)
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
                    point_ids=point_ids,
                )
            else:
                # print(response_message)
                return RunConversationResponse(
                    status=StatusCode.REGULAR_MESSAGE,
                    response=response_message.content,
                    sources=sources,
                    obtainedParams=obtained_params,
                    point_ids=point_ids,
                )
        except Exception as e:
            logger.error(f"LLM failed: {e}", exc_info=True)
            return RunConversationResponse(
                status=StatusCode.LLM_ERROR,
                response="Sorry, your request failed. Something went wrong with the LLM. Please try again.",
                obtainedParams=obtained_params,
                sources=sources if sources else [],
                point_ids=point_ids if point_ids else previous_vdb_ids,
            )

    async def call_tool(self, fn, args, user_onc_token):
        try:
            return await fn(**args, user_onc_token=user_onc_token)
        except TypeError:
            # fallback if fn doesn't accept user_onc_token
            return await fn(**args)
