from onc import ONC
from Environment import Environment


async def generate_download_codes(
    deviceCategory: str = None,
    locationCode: str = None,
    dataProductCode: str = None,
    extension: str = None,
    dateFrom: str = None,
    dateTo: str = None,
    user_onc_token: str = None,
    obtainedParams: dict = {},
):

    env = Environment()
    onc = ONC(user_onc_token) if user_onc_token else ONC(env.get_onc_token())
    """
    Get the device categoryCode at a certain locationCode at Cambridge Bay in a dataProduct with an extension, 
    so that users request to download data, over a specified time period.
    Returns a result of a data download request.
    This function simply queues a download from ONC, and gives no additional information to the LLM.
    If this function is called, the LLM will either tell the user that their download is queued, or that their download request
    was unsucessful.
    If the request is successful, the download is not necessarily successful, so do not tell the user if the download is successful or not.
    Returns:
        result (str): The result of the download request. It will either signify that the download was successful,
                      or that the download was unsuccessful, and you should inform the user of this result.
    Args:
        deviceCategory (str): An ONC defined code identifying each device.
        locationCode (str): An ONC defined code identifying each device site.
        dataProductCode (str): AN ONC defined code identifying the data type being delivered.
        extension (str): The format of the dataProduct to be delivered.
        dateFrom (str): ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')
        dateTo (str): ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')
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
    
    if deviceCategory is None and "deviceCategory" in obtainedParams:
        deviceCategory = obtainedParams.get("deviceCategory")
    if locationCode is None and "locationCode" in obtainedParams:
        locationCode = obtainedParams.get("locationCode")
    if dataProductCode is None and "dataProductCode" in obtainedParams:
        dataProductCode = obtainedParams.get("dataProductCode")
    if extension is None and "extension" in obtainedParams:
        extension = obtainedParams.get("extension")
    if dateFrom is None and "dateFrom" in obtainedParams:
        dateFrom = obtainedParams.get("dateFrom")
    if dateTo is None and "dateTo" in obtainedParams:
        dateTo = obtainedParams.get("dateTo")
    allParams = {
        "deviceCategory": deviceCategory, 
        "locationCode": locationCode, 
        "dataProductCode": dataProductCode, 
        "extension": extension, 
        "dateFrom": dateFrom, 
        "dateTo": dateTo
    }
    neededParams = []
    obtainedParams = {}
    for param, value in allParams.items():
        if value is None:
            neededParams.append(param) #finding the parameters that are not set
        else:
            obtainedParams[param] = value #remaking the obtainedParams dict
    if len(neededParams) > 0: #If need one or more parameters
        return {
            "status": "ParamsNeeded",
            "message": f"Hey! It looks like you want to do a data download! So far I have the following parameters: {', '.join(obtainedParams.keys())}. However, I still need you to please provide the following missing parameters so I can complete the data download request: {', '.join(neededParams)}. Thank you!",
            "obtainedParams": obtainedParams,
        }
    params = {
        "locationCode": locationCode,
        "deviceCategoryCode": deviceCategory,
        "dataProductCode": dataProductCode,
        "extension": extension,
        "dateFrom": dateFrom,
        "dateTo": dateTo,
        "dpo_qualityControl": "1", #1 means to clean the data, 0 means to not clean the data. Cleaning the data will use qaqc flags 3,4 and 6 to be replaced with Nans when dpo)dataGaps is set to 1. If its set to 0, then the data will be removed.
        "dpo_resample": "none",#No sampling done. If set to average, then the data will be averaged over the time period specified. This auto cleans the data. Same for minMax and minMaxAvg.
        #If using dpo_resample then can use for example dpo_minMaxAvg = {0, 60, 600, 900, 3600, 86400} to get 1 min, 10 min, 10 min, 15 min, 1 hour, and 1 day min, max and averages.
        "dpo_dataGaps": "1", #Fills missing/bad data with NaNs
    }
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
        response = (onc.requestDataProduct(params))
        print(f"Response from ONC: {response}")
        return {
            "status": "queued",
            "dpRequestId": response.dpRequestId,
            "doi": response.citations[0].doi,
            "citation": response.citations[0].citation,
            "message": "Your download is being processed. ",
        }
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "message": "Data is unavailable for this sensor and time. "
            "DO NOT ADVISE THE USER TO DO ANYTHING EXCEPT TRY AGAIN WITH DIFFERENT PARAMETERS.",
        }
