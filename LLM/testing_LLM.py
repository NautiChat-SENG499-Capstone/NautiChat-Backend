import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

if os.getenv("ENV") != "production":
    env_file_location = str(Path(__file__).resolve().parent / ".env")
    load_dotenv(env_file_location)
onc_token = os.getenv("ONC_TOKEN")

from LLM.Constants.status_codes import StatusCode
from LLM.core import LLM
from LLM.Environment import Environment
from LLM.RAG import RAG
from LLM.schemas import ObtainedParamsDictionary

logger = logging.getLogger(__name__)


async def main():
    env = Environment()
    RAG_instance = RAG(env)
    print("RAG instance created successfully.")
    try:
        LLM_Instance = LLM(
            env=env, RAG_instance=RAG_instance
        )  # Create an instance of the LLM class
        user_prompt = input("Enter your first question (or 'exit' to quit): ")
        chatHistory = []
        obtainedParams: ObtainedParamsDictionary = ObtainedParamsDictionary()
        point_ids: list[str] = []
        while user_prompt not in ["exit", "quit"]:
            response = await LLM_Instance.run_conversation(
                user_prompt=user_prompt,
                user_onc_token=onc_token,
                chat_history=chatHistory,
                obtained_params=obtainedParams,
                point_ids=point_ids,
            )
            print()
            print()
            print()
            print("Response from LLM:", response)
            if response.status == StatusCode.PROCESSING_DATA_DOWNLOAD:
                print("Download request initiated. Request ID:", response.dpRequestId)
                print("DOI:", response.doi)
                print("Citation:", response.citation)
            obtainedParams = response.obtainedParams
            point_ids = response.point_ids
            print("Response:", response.response)
            print("Obtained parameters:", obtainedParams)
            print("URL Params Used:", response.urlParamsUsed)
            print("Base URL:", response.baseUrl)
            response = {"role": "assistant", "content": response.response}
            chatHistory.append({"role": "user", "content": user_prompt})
            chatHistory.append(response)
            user_prompt = input("Enter your next question (or 'exit' to quit): ")
            if len(chatHistory) > 6:
                chatHistory = chatHistory[
                    -6:
                ]  # reducing chat history to last 3 conversations

    except Exception as e:
        print("Error occurred:", e)


if __name__ == "__main__":
    asyncio.run(main())
