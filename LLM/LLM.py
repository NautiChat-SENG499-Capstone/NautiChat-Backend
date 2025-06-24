import pandas as pd
import asyncio
import json
from datetime import datetime
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
    get_ship_noise_acoustic_for_date,
    get_wind_speed_at_timestamp,
    get_ice_thickness,
)
from RAG import RAG
from Environment import Environment
from Constants.toolDescriptions import toolDescriptions

class LLM:
    def __init__(
        self, env: Environment
        , RAG_instance: RAG = None
    ):
        self.client = env.get_client()  # Get the Groq client from the environment
        #self.model = env.get_model()  # Get the model to use from the environment
        self.model = "llama-3.1-8b-instant" #use this one when model limit is reached
        self.RAG_instance = RAG_instance if RAG_instance else RAG(env)  # Use provided RAG instance or create a new one
        self.available_functions = {
            "get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            "get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
            "get_deployed_devices_over_time_interval": get_deployed_devices_over_time_interval,
            "get_active_instruments_at_cambridge_bay": get_active_instruments_at_cambridge_bay,
            # "get_time_range_of_available_data": get_time_range_of_available_data
        }

    async def run_conversation(self, user_prompt, startingPrompt: str = None, chatHistory: list[dict] = []):
        try:
            #print("Starting conversation with user prompt:", user_prompt)
            CurrentDate = datetime.now().strftime("%Y-%m-%d")
            if startingPrompt is None:
                startingPrompt = f"You are a helpful assistant for Oceans Network Canada that can use tools. \
                    The current day is: {CurrentDate}. You can CHOOSE to use the given tools to obtain the data needed to answer the prompt and provide the results IF that is required. Dont summarize data unles asked to."

            #print(user_prompt)
            messages = chatHistory + [
                {
                    "role": "system",
                    "content": startingPrompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ]

            print("Calling vectorDB")
            vectorDBResponse = self.RAG_instance.get_documents(user_prompt)
            if isinstance(vectorDBResponse, pd.DataFrame):
                if vectorDBResponse.empty:
                    vector_content = ""
                else:
                    # Convert DataFrame to a more readable format
                    vector_content = vectorDBResponse.to_string(index=False)
            else:
                vector_content = str(vectorDBResponse)
            messages.append({
                "role": "system",
                "content": vector_content
                }) 
            
            response = self.client.chat.completions.create(
                model=self.model,  # LLM to use
                messages=messages,  # Conversation history
                stream=False,
                tools=toolDescriptions,  # Available tools (i.e. functions) for our LLM to use
                tool_choice="auto",  # Let our LLM decide when to use tools
                max_completion_tokens=4096,  # Maximum number of tokens to allow in our response
                temperature=0.25,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
            )
            #print("resp:", response)
            response_message = response.choices[0].message
            # print(vector_content)
            tool_calls = response_message.tool_calls
            # print(tool_calls)
            if tool_calls:
                #print("Tool calls detected, processing...")
                for tool_call in tool_calls:
                    # print(tool_call)
                    # print()
                    function_name = tool_call.function.name

                    if function_name in self.available_functions:
                        function_args = json.loads(tool_call.function.arguments)
                        print(f"Calling function: {function_name} with args: {function_args}")
                        if not function_args:
                            function_response = await self.available_functions[function_name]()
                        else:
                            function_response = await self.available_functions[function_name](**function_args)
                        #print(f"Function response: {function_response}")
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",  # Indicates this message is from tool use
                                "name": function_name,
                                "content": json.dumps(function_response),
                            }
                        )  # May be able to use this for getting most recent data if needed.
                #print("Messages after tool calls:", messages)
                second_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_completion_tokens=4096,
                    temperature=0.25
                )  # Calls LLM again with all the data from all functions
                # Return the final response
                #print("Second response:", second_response)
                return second_response.choices[0].message.content
            else:
                return response_message.content
        except:
            return "Sorry, your request failed. Please try again."
    


async def main():

    env = Environment()
    RAG_instance = RAG(env)
    print("RAG instance created successfully.")
    try:
        LLM_Instance = LLM(env=env, RAG_instance=RAG_instance)  # Create an instance of the LLM class
        user_prompt = input("Enter your first question (or 'exit' to quit): ")
        chatHistory = []
        while user_prompt not in ["exit", "quit"]:
            response = await LLM_Instance.run_conversation(user_prompt=user_prompt, chatHistory=chatHistory)
            print(response)
            response = {"role": "system", "content": response}
            #chatHistory.append(response)
            user_prompt = input("Enter your next question (or 'exit' to quit): ")
    except Exception as e:
        print("Error occurred:", e)


if __name__ == "__main__":
    asyncio.run(main())
