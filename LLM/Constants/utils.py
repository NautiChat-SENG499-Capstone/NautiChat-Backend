from LLM.Constants.status_codes import StatusCode
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse, ToolCall

resample_periods = [
    1,
    5,
    10,
    15,
    30,
    60,
    300,
    600,
    900,
    1800,
    3600,
    7200,
    14400,
    21600,
    43200,
    86400,
    172800,
    259200,
    604800,
    1209600,
    2592000,
]


def create_user_call(
    user_prompt: str, vector_content: str, toolInfo: list[ToolCall] = None
) -> str:
    user_input = f"""(Sensor Information from Vector Search for context only):
            {vector_content}

            Using the above information, answer the following question:
            {user_prompt}
        """
    if toolInfo:
        user_input += "\nHere is the data retrieved from tools you would have called:"
        user_input += "\n".join(
            [
                f"Function Name: {call.function_name}\nArguments: {call.arguments}\nResponse: {call.response}"
                for call in toolInfo
            ]
        )
    return user_input


def sync_param(field_name: str, local_value, params_model, all_obtained_params: dict):
    """
    Sync a local variable with a field in a Pydantic model:
    - If local_value is None, try to pull from model.
    - If local_value is not None, update model with it.
    - Update all_obtained_params with the field_name and local_value when local_value is not None.
    Returns the resolved value.
    """
    if local_value is None:
        local_value = getattr(params_model, field_name, None)
    else:
        setattr(params_model, field_name, local_value)
    if local_value is not None:
        all_obtained_params[field_name] = local_value
    return local_value


def handle_plotting_requests(
    function_response: dict,
    sources: list,
    obtained_params: ObtainedParamsDictionary,
    point_ids: list[str] = None,
) -> RunConversationResponse:
    if function_response.get("status") == StatusCode.PROCESSING_DATA_DOWNLOAD:
        return RunConversationResponse(
            status=StatusCode.PROCESSING_DATA_DOWNLOAD,
            response=function_response.get(
                "response", "Your download is being processed."
            ),
            dpRequestId=function_response.get("dpRequestId"),
            doi=function_response.get("doi"),
            citation=function_response.get("citation"),
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get("baseUrl", ""),
            obtainedParams=obtained_params,
            sources=sources if sources else [],
            point_ids=point_ids,
        )
    else:
        return RunConversationResponse(
            status=StatusCode.REGULAR_MESSAGE,
            response=function_response.get("response", ""),
            obtainedParams=obtained_params,
            sources=sources if sources else [],
            point_ids=point_ids,
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get("baseUrl", ""),
        )


def handle_scalar_request(
    function_response: dict,
    sources: list,
    scalar_request_status: int,
    point_ids: list[str] = None,
) -> RunConversationResponse:
    if scalar_request_status == StatusCode.PARAMS_NEEDED:
        print("Scalar request parameters needed, returning response now")
        obtained_params: ObtainedParamsDictionary = function_response.get(
            "obtainedParams", {}
        )
        # Return a response indicating that Paramaters are needed
        return RunConversationResponse(
            status=StatusCode.PARAMS_NEEDED,
            response=function_response.get("response"),
            obtainedParams=obtained_params,
            sources=sources,
            point_ids=point_ids,
        )
    elif scalar_request_status == StatusCode.DEPLOYMENT_ERROR:
        print("Scalar request parameters needed, returning response now")
        obtained_params: ObtainedParamsDictionary = function_response.get(
            "obtainedParams", {}
        )
        print(function_response.get("result"))
        # Return a response indicating that Paramaters are needed
        return RunConversationResponse(
            status=StatusCode.DEPLOYMENT_ERROR,
            response=function_response.get("response"),
            obtainedParams=obtained_params,
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get(
                "baseUrl",
                "https://data.oceannetworks.ca/api/scalardata/location?",
            ),
            sources=sources,
            point_ids=point_ids,
        )
    elif scalar_request_status == StatusCode.NO_DATA:
        print("No data returned.")
        obtained_params: ObtainedParamsDictionary = function_response.get(
            "obtainedParams", {}
        )
        print("Obtained parameters:", obtained_params)
        print("Obtained parameters:", type(obtained_params))
        # Return a response indicating that Paramaters are needed
        return RunConversationResponse(
            status=StatusCode.DEPLOYMENT_ERROR,
            response=function_response.get("response"),
            obtainedParams=obtained_params,
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get(
                "baseUrl",
                "https://data.oceannetworks.ca/api/scalardata/location?",
            ),
            sources=sources,
            point_ids=point_ids,
        )
    elif scalar_request_status == StatusCode.SCALAR_REQUEST_ERROR:
        print("No data returned.")
        obtained_params: ObtainedParamsDictionary = function_response.get(
            "obtainedParams", {}
        )
        print("Obtained parameters:", obtained_params)
        print("Obtained parameters:", type(obtained_params))
        # Return a response indicating that Paramaters are needed
        return RunConversationResponse(
            status=StatusCode.SCALAR_REQUEST_ERROR,
            response=function_response.get("response"),
            obtainedParams=obtained_params,
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get(
                "baseUrl",
                "https://data.oceannetworks.ca/api/scalardata/location?",
            ),
            sources=sources,
            point_ids=point_ids,
        )


def handle_data_download(
    function_response: dict,
    sources: list,
    point_ids: list[str] = None,
) -> RunConversationResponse:
    data_download_status = function_response.get("status")
    if data_download_status == StatusCode.PARAMS_NEEDED:
        print("Download parameters needed, returning response now")
        obtained_params: ObtainedParamsDictionary = function_response.get(
            "obtainedParams", {}
        )
        print("Obtained parameters:", obtained_params)
        print("Obtained parameters:", type(obtained_params))
        # Return a response indicating that Paramaters are needed
        return RunConversationResponse(
            status=StatusCode.PARAMS_NEEDED,
            response=function_response.get("response"),
            obtainedParams=obtained_params,
            sources=sources,
            point_ids=point_ids,
        )
    elif data_download_status == StatusCode.PROCESSING_DATA_DOWNLOAD:
        print("download done so returning response now")
        dpRequestId = function_response.get("dpRequestId")
        doi = function_response.get("doi", "No DOI available")
        citation = function_response.get("citation", "No citation available")
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary()
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
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get(
                "baseUrl",
                "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
            ),
            sources=sources,
            point_ids=point_ids,
        )
    elif data_download_status == StatusCode.ERROR_WITH_DATA_DOWNLOAD:
        print("Download error so returning response now")
        obtained_params: ObtainedParamsDictionary = function_response.get(
            "obtainedParams", {}
        )
        # Return a response indicating that there was an error with the download
        return RunConversationResponse(
            status=StatusCode.ERROR_WITH_DATA_DOWNLOAD,
            response=function_response.get(
                "response",
                "An error occurred while processing your download request.",
            ),
            obtainedParams=obtained_params,
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get(
                "baseUrl",
                "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
            ),
            sources=sources,
            point_ids=point_ids,
        )
