from datetime import datetime
import logging
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
import sys
import pandas as pd
import json
from LLM.toolsSprint1 import (
    get_properties_at_cambridge_bay,
    get_daily_sea_temperature_stats_cambridge_bay,
    get_deployed_devices_over_time_interval,
    get_active_instruments_at_cambridge_bay,
    # get_time_range_of_available_data,
)
from LLM.toolsSprint2 import (
    get_daily_air_temperature_stats_cambridge_bay,
    get_oxygen_data_24h,
    # get_ship_noise_acoustic_for_date,
    get_wind_speed_at_timestamp,
    get_ice_thickness,
)
from LLM.codes import generate_download_codes
from LLM.RAG import RAG, JinaEmbeddings
from LLM.Constants.toolDescriptions import toolDescriptions

logger = logging.getLogger(__name__)

sys.modules["LLM"] = sys.modules[__name__]
dpRequestId: str = ""


def set_request_id(value: str) -> None:
    global dpRequestId
    dpRequestId = value


def get_request_id():
    return dpRequestId


class LLM:
    __shared: dict[str, object] | None = None
    # singleton cache

    def __init__(self, env, *, RAG_instance=None):
        self.env = env
        self.client = env.get_client()
        self.model = env.get_model()
        self.model = "llama-3.1-8b-instant"

        if LLM.__shared is None:
            logging.info("First LLM() building shared embedder/cross-encoder")
            LLM.__shared = {
                "embedder": JinaEmbeddings(),
                "cross": HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base"),
            }

        shared = LLM.__shared
        self.RAG_instance = RAG_instance or RAG(
            env,
            embedder=shared["embedder"],
            cross_encoder=shared["cross"],
        )
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
        self, user_prompt, startingPrompt: str = None, chatHistory: list[dict] = [], user_onc_token: str = None
    ) -> dict:
        try:
            set_request_id("")
            CurrentDate = datetime.now().strftime("%Y-%m-%d")
            if startingPrompt is None:
                startingPrompt = f"""
                You are a helpful assistant for Ocean Networks Canada that uses tools to answer user queries when needed. 
                Today’s date is {CurrentDate}. You can CHOOSE to use the given tools to obtain the data needed to answer the prompt and provide the results IF that is required.
                Dont summarize data unless asked to.

                You may use tools when required to answer user questions. Do not describe what you *will* do — only use tools if needed.

                When a tool is used, DO NOT continue reasoning or take further steps based on its result.

                Instead, return a final response to the user that clearly and colloquially explains the tool's result — without guessing, adding advice, or planning further steps. Stay within the limits of the message returned by the tool.

                DO NOT speculate or describe what might happen next.

                You are NEVER required to generate code in any language.


                Do NOT add follow-up suggestions, guesses, or recommendations.

                DO NOT guess what the tool might return.
                DO NOT say "I will now use the tool".
                DO NOT try to reason about data availability.
                Here is the user_onc_token: {user_onc_token}.
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
            print("Response from LLM:", response)
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            # print(tool_calls)
            DownloadDone = False
            if tool_calls:
                # print("Tool calls detected, processing...")
                print("tools calls:", tool_calls)
                for tool_call in tool_calls:
                    # print(tool_call)
                    # print()
                    function_name = tool_call.function.name

                    if function_name in self.available_functions:
                        if function_name == "generate_download_codes":
                            # Special case for download codes
                            print("Generating download codes...")
                            set_request_id("")
                            DownloadDone = True
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                        print(f"Calling function: {function_name} with args: {function_args}")
                        function_response = await self.call_tool(
                            self.available_functions[function_name],
                            function_args or {},
                            user_onc_token=user_onc_token or self.env.get_onc_token(),
                        )
                        if(DownloadDone):
                            print("download done so returning response now")
                            DownloadDone = False
                            function_response = {
                                "status": 201,
                                "response": "Your download is being processed. ",
                                "dpRequestId": get_request_id(),
                            }
                            return function_response
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
                print("Second response:", second_response)
                response = second_response.choices[0].message.content
                if dpRequestId:
                    return {
                        "status": 201,
                        "response": response,
                        "dpRequestId": dpRequestId,
                    }
                else:
                    return {
                        "status": 200,
                        "response": response,
                    }
            else:
                print(response_message)
                return {"status": 200, "response": response_message.content}
        except Exception as e:
            logger.error(f"LLM failed: {e}", exc_info=True)
            return {
                "status": 400,
                "response": "Sorry, your request failed. Please try again.",
            }

    async def call_tool(self, fn, args, user_onc_token):
        try:
            return await fn(**args, user_onc_token=user_onc_token)
        except TypeError:
            # fallback if fn doesn't accept user_onc_token
            return await fn(**args)


# async def main():

#     env = Environment()
#     RAG_instance = RAG(env)
#     print("RAG instance created successfully.")
#     try:
#         LLM_Instance = LLM(env=env, RAG_instance=RAG_instance)  # Create an instance of the LLM class
#         user_prompt = input("Enter your first question (or 'exit' to quit): ")
#         chatHistory = []
#         while user_prompt not in ["exit", "quit"]:
#             response = await LLM_Instance.run_conversation(user_prompt=user_prompt, chatHistory=chatHistory)
#             print(response)
#             response = {"role": "system", "content": response}
#             user_prompt = input("Enter your next question (or 'exit' to quit): ")

#     except Exception as e:
#         print("Error occurred:", e)


# if __name__ == "__main__":
#     asyncio.run(main())
