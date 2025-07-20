import json
import logging
import sys
from collections import OrderedDict
from datetime import datetime

import pandas as pd

# from langchain.output_parsers import PydanticOutputParser
from LLM.Constants.status_codes import StatusCode
from LLM.Constants.system_prompts import (
    generate_system_prompt,
    system_prompt_final_response,
    system_prompt_reasoning,
    system_prompt_tool_execution,
    system_prompt_uncertain,
)
from LLM.Constants.tool_descriptions import toolDescriptions  # , toolDescriptionsShort
from LLM.data_download import generate_download_codes

# from LLM.utils import update_date_to
from LLM.RAG import RAG
from LLM.schemas import (
    ObtainedParamsDictionary,
    PlanningResponse,
    RunConversationResponse,
    ToolCall,
    ToolCallList,
    parse_llm_response,
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
# parser = PydanticOutputParser(pydantic_object=PlanningResponse)
# formatInstructions = parser.get_format_instructions()
formatPlanningInstructions = PlanningResponse.model_json_schema()
formatToolCallingInstructions = ToolCall.model_json_schema()


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

    async def run_planning(
        self,
        currentDate: str,
        user_prompt: str,
        chat_history: list[dict] = [],
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary(),
    ):
        systemPromptReasoning = generate_system_prompt(
            system_prompt_reasoning,
            context={
                "current_date": currentDate,
                "obtained_params": json.dumps(
                    obtained_params.model_dump(exclude_none=True)
                ),
                "format_instructions": formatPlanningInstructions,
                "tool_descriptions": json.dumps(toolDescriptions),
            },
        )
        messages = [
            {
                "role": "system",
                "content": systemPromptReasoning,
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
        structured_output = parse_llm_response(response_message, PlanningResponse)
        print("Structured Output:", structured_output)
        print()
        print()
        print()
        reasoning = structured_output.reasoning
        inputs_uncertain = structured_output.inputs_uncertain
        inputs_missing = structured_output.inputs_missing
        tools_needed = structured_output.tools_needed
        inputs_provided = structured_output.inputs_provided
        # print("Reasoning:", reasoning)
        # print()
        # print()
        # print()
        # print("Inputs Needed:", inputs_needed)
        # print()
        # print()
        # print()
        return (
            reasoning,
            tools_needed,
            inputs_provided,
            inputs_missing,
            inputs_uncertain,
        )

    async def handle_uncertain_inputs(
        self,
        inputs_uncertain: dict,
    ) -> RunConversationResponse:
        systemPromptUncertain = generate_system_prompt(
            system_prompt_uncertain,
            context={
                "inputs_uncertain": inputs_uncertain,
            },
        )
        messages = [
            {
                "role": "system",
                "content": systemPromptUncertain,
            },
        ]
        response = self.client.chat.completions.create(
            model=self.model,  # LLM to use
            messages=messages,  # Includes Conversation history
            stream=False,
            max_completion_tokens=512,  # Maximum number of tokens to allow in our response
            temperature=0,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
        )
        response_message = response.choices[0].message.content

        return RunConversationResponse(
            status=StatusCode.REGULAR_MESSAGE, response=response_message, sources=[]
        )

    async def handle_tool_calls(
        self,
        currentDate,
        tool_reasoning,
        inputs_provided,
        inputs_missing,
        vector_content,
        user_onc_token=None,
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary(),
    ) -> dict:
        systemPromptToolExecution = generate_system_prompt(
            system_prompt_tool_execution,
            context={
                "current_date": currentDate,
                # "format_instructions": formatToolCallingInstructions,
                "reasoning": tool_reasoning,
                "inputs_provided": inputs_provided,
                "inputs_missing": inputs_missing,
                "vector_db_results": vector_content,
            },
        )

        messages = [
            {
                "role": "system",
                "content": systemPromptToolExecution,
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model,  # LLM to use
            messages=messages,  # Includes Conversation history
            stream=False,
            # tools=toolDescriptions,  # Available tools (i.e. functions) for our LLM to use
            # tool_choice="auto",  # Let our LLM decide when to use tools
            max_completion_tokens=1024,  # Maximum number of tokens to allow in our response
            temperature=0,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
        )
        response_message = response.choices[0].message.content
        print("Response from tool calling LLM:", response_message)
        tool_calls = parse_llm_response(response_message, ToolCallList)

        doing_data_download = False
        tool_calls = tool_calls.tools
        print("Tool Calls:", tool_calls)
        if tool_calls:
            print("Tool calls detected, processing...")
            print("tools calls:", tool_calls)
            tool_calls = list(
                OrderedDict(((call.name), call) for call in tool_calls).values()
            )
            print("Unique tool calls:", tool_calls)
            toolMessages = []
            baseUrlList = []
            urlParamsUsedList = []
            for tool_call in tool_calls:
                # print(tool_call)
                # print()
                function_name = tool_call.name
                print("Function name:", function_name)
                print("Function arguments:", tool_call.arguments)
                # tool_call_json = tool_call.model_dump_json(indent=2)
                # print("Tool call JSON:", tool_call_json)
                # print("Function name:", tool_call_json["name"])
                # print("Function arguments:", tool_call_json["arguments"])

                if function_name in self.available_functions:
                    if function_name == "generate_download_codes":
                        # Special case for download codes
                        print("Generating download codes...")
                        doing_data_download = True
                    try:
                        function_args = tool_call.arguments
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
                    baseUrlList.append(
                        function_response.get(
                            "baseUrl",
                            "",
                        )
                    )
                    urlParamsUsedList.append(function_response.get("urlParamsUsed", {}))

                    print("Function response:", function_response)
                    if doing_data_download:
                        DataDownloadStatus = function_response.get("status")
                        if DataDownloadStatus == StatusCode.PARAMS_NEEDED:
                            print("Download parameters needed, returning response now")
                            obtained_params: ObtainedParamsDictionary = (
                                function_response.get("obtained_params", {})
                            )
                            print("Obtained parameters:", obtained_params)
                            print("Obtained parameters:", type(obtained_params))
                            # Return a response indicating that Paramaters are needed
                            return {
                                "status": StatusCode.PARAMS_NEEDED,
                                "response": function_response.get("response"),
                                "obtained_params": obtained_params,
                            }
                        elif DataDownloadStatus == StatusCode.PROCESSING_DATA_DOWNLOAD:
                            print("download done so returning response now")
                            dpRequestId = function_response.get("dpRequestId")
                            doi = function_response.get("doi", "No DOI available")
                            citation = function_response.get(
                                "citation", "No citation available"
                            )
                            # Return a response indicating that the download is being processed
                            return {
                                "status": StatusCode.PROCESSING_DATA_DOWNLOAD,
                                "response": function_response.get(
                                    "response", "Your download is being processed."
                                ),
                                "dpRequestId": dpRequestId,
                                "doi": doi,
                                "citation": citation,
                                "urlParamsUsed": function_response.get(
                                    "urlParamsUsed", {}
                                ),
                                "baseUrl": function_response.get(
                                    "baseUrl",
                                    "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
                                ),
                            }
                        elif DataDownloadStatus == StatusCode.ERROR_WITH_DATA_DOWNLOAD:
                            print("Download error so returning response now")
                            obtained_params: ObtainedParamsDictionary = (
                                function_response.get("obtained_params", {})
                            )
                            # Return a response indicating that there was an error with the download
                            return {
                                "status": StatusCode.ERROR_WITH_DATA_DOWNLOAD,
                                "response": function_response.get(
                                    "response",
                                    "An error occurred while processing your download request.",
                                ),
                                "obtained_params": obtained_params,
                                "urlParamsUsed": function_response.get(
                                    "urlParamsUsed", {}
                                ),
                                "baseUrl": function_response.get(
                                    "baseUrl",
                                    "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
                                ),
                            }
                    else:
                        # Not doing data download so clearing the obtained_params
                        obtained_params: ObtainedParamsDictionary = (
                            ObtainedParamsDictionary()
                        )

                    toolMessages.append(
                        {
                            "tool_call_id": str(tool_call.id),
                            "role": "tool",  # Indicates this message is from tool use
                            "name": function_name,
                            "content": json.dumps(
                                function_response.get("response", "")
                            ),
                        }
                    )  # May be able to use this for getting most recent data if needed.
            return {
                "status": StatusCode.TOOL_CALLS,
                "toolMessages": toolMessages,
                "baseUrls": baseUrlList,
                "urlParamsUsed": urlParamsUsedList,
            }
        else:
            return {
                "status": StatusCode.REGULAR_MESSAGE,
                "response": "No tool calls detected. Please try again with a different query.",
            }

    async def run_final_response(
        self,
        currentDate: str,
        user_prompt: str,
        chat_history: list[dict] = [],
        vector_content: str = "",
        toolMessages: list[dict] = None,
        urlParamsUsedList: list[dict] = [],
        baseUrlList: list[str] = [],
        sources: list[str] = [],
    ) -> RunConversationResponse:
        systemPromptFinalResponse = generate_system_prompt(
            system_prompt_final_response,
            context={
                "current_date": currentDate,
            },
        )
        messagesNoContext = [
            {
                "role": "system",
                "content": systemPromptFinalResponse,
            },
            *chat_history,
            {"role": "assistant", "content": vector_content},
        ]
        if toolMessages:
            messagesNoContext.extend(
                toolMessages
            )  # Add tool messages to the conversation
        messagesNoContext.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )  # Add the user prompt to the conversation
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
        if toolMessages:
            return RunConversationResponse(
                status=StatusCode.REGULAR_MESSAGE,
                response=response,
                urlParamsUsed=urlParamsUsedList[0] if urlParamsUsedList else "",
                baseUrl=baseUrlList[0] if baseUrlList else "",
                sources=sources,
            )
        else:
            print(response)
            return RunConversationResponse(
                status=StatusCode.REGULAR_MESSAGE,
                response=response,
                sources=sources,
            )

    async def run_conversation(
        self,
        user_prompt: str,
        user_onc_token: str,
        chat_history: list[dict] = [],
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary(),
    ) -> RunConversationResponse:
        try:
            sources = []
            currentDate = datetime.now().strftime("%Y-%m-%d")
            (
                reasoning,
                tools_needed,
                inputs_provided,
                inputs_missing,
                inputs_uncertain,
            ) = await self.run_planning(
                currentDate, user_prompt, chat_history, obtained_params
            )
            if inputs_uncertain:
                return await self.handle_uncertain_inputs(inputs_uncertain)

            VectorDBinput = "User: " + user_prompt + "Assistant: " + str(inputs_missing)
            vectorDBResponse = self.RAG_instance.get_documents(VectorDBinput)
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

            toolMessages = None
            urlParamsUsedList = []
            baseUrlList = []
            if tools_needed:
                print("NEED INPUTS")
                print("obtained Params before tools called: ", obtained_params)
                response = await self.handle_tool_calls(
                    currentDate=currentDate,
                    tool_reasoning=reasoning,
                    inputs_provided=inputs_provided,
                    inputs_missing=inputs_missing,
                    vector_content=vector_content,
                    user_onc_token=user_onc_token,
                    obtained_params=obtained_params,
                )
                print("obtained Params after tools called: ", obtained_params)
                if response.get("status") == StatusCode.TOOL_CALLS:
                    toolMessages = response.get("toolMessages", [])
                    urlParamsUsedList = response.get("urlParamsUsed", [])
                    baseUrlList = response.get("baseUrls", [])
                    print("Tool Messages:", toolMessages)
                    if not toolMessages:
                        print(
                            "No tool messages returned from handle_tool_calls, something went wrong."
                        )
                        raise Exception(
                            "No tool messages returned from handle_tool_calls, something went wrong."
                        )
                elif (
                    not response.get("status") == StatusCode.REGULAR_MESSAGE
                ):  # if the status is not REGULAR_MESSAGE, it means we have a special case like PARAMS_NEEDED or PROCESSING_DATA_DOWNLOAD which we just want to return
                    response["sources"] = sources
                    return RunConversationResponse.model_validate(response)
                else:
                    toolMessages = None
            return await self.run_final_response(
                currentDate,
                user_prompt,
                chat_history,
                vector_content,
                toolMessages,
                urlParamsUsedList,
                baseUrlList,
                sources,
            )  # The final response is the last step where we call the LLM again with all the data from all functions and the user prompt

        except Exception as e:
            logger.error(f"LLM failed: {e}", exc_info=True)
            return RunConversationResponse(
                status=StatusCode.LLM_ERROR,
                response="Sorry, your request failed. Something went wrong with the LLM. Please try again.",
                sources=sources,
            )

    async def call_tool(self, fn, args, user_onc_token):
        try:
            return await fn(**args, user_onc_token=user_onc_token)
        except TypeError:
            # fallback if fn doesn't accept user_onc_token
            return await fn(**args)
