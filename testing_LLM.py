import asyncio
import logging

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
        while user_prompt not in ["exit", "quit"]:
            response = await LLM_Instance.run_conversation(
                user_prompt=user_prompt,
                user_onc_token="6a316121-e017-4f4c-9cb1-eaf5dd706425",
                chatHistory=chatHistory,
                obtainedParams=obtainedParams,
            )
            print()
            print()
            print()
            print("Response from LLM:", response)
            if response.status == StatusCode.PROCESSING_DATA_DOWNLOAD:
                print("Download request initiated. Request ID:", response.dpRequestId)
                print("DOI:", response.doi)
                print("Citation:", response.citation)
                obtainedParams: ObtainedParamsDictionary = ObtainedParamsDictionary()
            elif (
                response.status == StatusCode.PARAMS_NEEDED
                or response.status == StatusCode.DEPLOYMENT_ERROR
            ):
                print("Error:", response.response)
                obtainedParams = response.obtainedParams
                print("Obtained parameters:", obtainedParams)
            else:
                print("Response:", response.response)
            print("URL Params Used:", response.urlParamsUsed)
            print("Base URL:", response.baseUrl)
            response = {"role": "assistant", "content": response.response}
            chatHistory.append({"role": "user", "content": user_prompt})
            chatHistory.append(response)
            user_prompt = input("Enter your next question (or 'exit' to quit): ")

    except Exception as e:
        print("Error occurred:", e)


if __name__ == "__main__":
    asyncio.run(main())
