from LLM.Constants.status_codes import StatusCode
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse

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


def handle_scalar_request(
    function_response: dict, sources: list, scalar_request_status: int
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
                "https://data.oceannetworks.ca/api/scalardata/location",
            ),
            sources=sources,
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
            response=function_response.get("description"),
            obtainedParams=obtained_params,
            urlParamsUsed=function_response.get("urlParamsUsed", {}),
            baseUrl=function_response.get(
                "baseUrl",
                "https://data.oceannetworks.ca/api/scalardata/location",
            ),
            sources=sources,
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
                "https://data.oceannetworks.ca/api/scalardata/location",
            ),
            sources=sources,
        )


def handle_data_download(
    function_response: dict, sources: list
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
        )
