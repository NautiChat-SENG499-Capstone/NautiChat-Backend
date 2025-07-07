from Constants.status_codes import StatusCode
from onc import ONC
from schemas import ObtainedParamsDictionary


def sync_param(field_name: str, local_value, params_model):
    """
    Sync a local variable with a field in a Pydantic model:
    - If local_value is None, try to pull from model.
    - If local_value is not None, update model with it.
    Returns the resolved value.
    """
    if local_value is None:
        return getattr(params_model, field_name, None)
    else:
        setattr(params_model, field_name, local_value)
        return local_value


async def generate_download_codes(
    user_onc_token: str,
    deviceCategoryCode: str = None,
    locationCode: str = None,
    dataProductCode: str = None,
    extension: str = None,
    dateFrom: str = None,
    dateTo: str = None,
    obtainedParams: ObtainedParamsDictionary = {},
):
    onc = ONC(user_onc_token)
    """
        Get the deviceCategoryCode at a certain locationCode at Cambridge Bay in a dataProduct with an extension,
        so that users request to download data, over a specified time period.
        Returns a result of a data download request.

        This function simply queues a download from ONC, and gives no additional information to the LLM.
        If this function is called, the LLM will only provide the parameters the user has explicitly given.
        Do not guess, assume, or invent any missing parameters.
        If parameters are missing, the function will handle asking the user for them.

        If the request is successful, it means the download has been queued — it does not mean the data will actually be delivered successfully.
        The LLM is not responsible for interpreting the result or following up.

        Returns:
            result (str): The result of the download request. It will either signify that the request has been queued,
                        that required parameters are missing, or that the request was unsuccessful.

        Args:
            deviceCategoryCode (str): An ONC-defined code identifying the type of device 
                                    (e.g., DIVE_COMPUTER, NAV, ROV_CAMERA, ACOUSTICRECEIVER, ADCP1200KHZ).
            locationCode (str): An ONC-defined code identifying the location of the device 
                                (e.g., 'CBYDS' for the Cambridge Bay Diver data or 'CBYIP' for the Cambridge Bay Underwater Network or 'CBYSP' for the Cambridge Bay Safe Passage Buoy or 'CBYSS' for the Cambridge Bay Shore Station).
            dataProductCode (str): An ONC-defined code identifying the type of data being requested 
                                (e.g., 'LF' for Log File, 'TSSD' for Time Series Scalar Data).
            extension (str): The file format of the data product to be delivered 
                            (e.g., 'csv', 'pdf', 'jpg', 'zip', 'flac', 'mp4', etc.).
            dateFrom (str): The start date of the data request in ISO 8601 format 
                            (e.g., '2016-06-01T00:00:00.000Z'). (YYYY-MM-DDTHH:MM:SS.sssZ)
            dateTo (str): The end date of the data request in ISO 8601 format 
                    (e.g., '2016-09-30T23:59:59.999Z'). (YYYY-MM-DDTHH:MM:SS.sssZ)
    """

    """
        NOTE: data download only actually requires the following parameters:
        dataProductCode, extension, dateFrom, dateTo.
        Acceptable dates/times conform to the ISO 8601 standard.
        The rest are optional.
        We probably want locationCode too though.
        Can create URL by appending each paramater to the base URL:
        https://data.oceannetworks.ca/api/dataProductDelivery/request?dataProductCode=
        add dataProductCode first then do ex:
        + "&extension=" + extension
        + "&dateFrom=" + dateFrom
        + "&dateTo=" + dateTo 
        Dont forget to append ONC token at the end of the URL
    """

    deviceCategoryCode = sync_param(
        "deviceCategoryCode", deviceCategoryCode, obtainedParams
    )
    locationCode = sync_param("locationCode", locationCode, obtainedParams)
    dataProductCode = sync_param("dataProductCode", dataProductCode, obtainedParams)
    extension = sync_param("extension", extension, obtainedParams)
    dateFrom = sync_param("dateFrom", dateFrom, obtainedParams)
    dateTo = sync_param("dateTo", dateTo, obtainedParams)

    allParams = {
        "dataProductCode": dataProductCode,
        "extension": extension,
        "dateFrom": dateFrom,
        "dateTo": dateTo,
    }  # Only the necessary parameters for a data download request.
    neededParams = []
    obtainedParams = {}
    for param, value in allParams.items():
        if value is None:
            neededParams.append(param)  # finding the parameters that are not set
        else:
            obtainedParams[param] = value  # remaking the obtainedParams dict
    for param, value in obtainedParams.items():
        if value is not None:
            obtainedParams[param] = value
    if len(neededParams) > 0:  # If need one or more parameters
        return {
            "status": StatusCode.PARAMS_NEEDED,
            "response": f"Hey! It looks like you want to do a data download! So far I have the following parameters: {', '.join(obtainedParams.keys())}. However, I still need you to please provide the following missing parameters so I can complete the data download request: {', '.join(neededParams)}. Thank you!",
            "obtainedParams": obtainedParams,
        }
    params = {
        "dataProductCode": dataProductCode,
        "extension": extension,
        "dateFrom": dateFrom,
        "dateTo": dateTo,
    }

    #  "dpo_qualityControl": "1", #1 means to clean the data, 0 means to not clean the data. Cleaning the data will use qaqc flags 3,4 and 6 to be replaced with Nans when dpo)dataGaps is set to 1. If its set to 0, then the data will be removed.
    #  "dpo_resample": "none",#No sampling done. If set to average, then the data will be averaged over the time period specified. This auto cleans the data. Same for minMax and minMaxAvg.
    #  #If using dpo_resample then can use for example dpo_minMaxAvg = {0, 60, 600, 900, 3600, 86400} to get 1 min, 10 min, 10 min, 15 min, 1 hour, and 1 day min, max and averages.
    #  "dpo_dataGaps": "1", #Fills missing/bad data with NaNs
    if "dpo_qualityControl" in obtainedParams:
        params["dpo_qualityControl"] = obtainedParams["dpo_qualityControl"]
    if "dpo_resample" in obtainedParams:
        params["dpo_resample"] = obtainedParams["dpo_resample"]
    if "dpo_dataGaps" in obtainedParams:
        params["dpo_dataGaps"] = obtainedParams["dpo_dataGaps"]
    if deviceCategoryCode is not None:
        params["deviceCategoryCode"] = deviceCategoryCode
    if locationCode is not None:
        params["locationCode"] = locationCode
    """
    https://wiki.oceannetworks.ca/spaces/DP/pages/40206402/Resampling+Data+Files 
    dpo_resample=minMax and dpo_minMax={0, 60, 600, 900, 3600, 86400}
    Min/Max+Avg - the combination of the min/max and average as described above. 
    The average is always calculated from clean data (if raw is selected it will apply for the min/max but the average will be clean). 
    The average values will be NaN if there is less than 70% data available after cleaning. 
    QAQC flags for min/max+avg with automatic resampling are the worst flag in the resample period, 
    which includes the 70% check on data completeness (except for engineering data or data from irregular or scheduled sampling). 
    This is the default option for time series scalar data.

    Note that tides are not filtered out in resampled products.
    """
    try:
        response = onc.requestDataProduct(params)
        print(f"Response from ONC: {response}")
        return {
            "status": StatusCode.PROCESSING_DATA_DOWNLOAD,
            "dpRequestId": response["dpRequestId"],
            "doi": response["citations"][0]["doi"],
            "citation": response["citations"][0]["citation"],
            "response": "Your download is being processed.",
            "urlParamsUsed": obtainedParams,
            "baseUrl": "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
        }
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        return {
            "status": StatusCode.ERROR_WITH_DATA_DOWNLOAD,
            "response": "Data is unavailable for this sensor and time.",
        }
