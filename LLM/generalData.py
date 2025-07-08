from onc import ONC
from Environment import Environment #add . at start to work in prod.
from Constants.statusCodes import StatusCode


async def get_data(
    deviceCategoryCode: str = None,
    locationCode: str = None,
    propertyCode: str = None,
    dateFrom: str = None,
    dateTo: str = None,
    user_onc_token: str = None,
    resamplePeriod: str = None,
    resampleType: str = None,
    obtainedParams: dict = {},
):

    env = Environment()
    onc = ONC(user_onc_token) if user_onc_token else ONC(env.get_onc_token())
    """
        Get the deviceCategoryCode at a certain locationCode at Cambridge Bay in a propertyCode with a resamplePeriod and resampleType,
        so that users can request scalar data, over a specified time period.
        Returns a result of a scalar data request.

        This function performs a data request to the ONC API, then returns the data to the LLM.
        If this function is called, the LLM will only provide the parameters the user has explicitly given.
        Do not guess, assume, or invent any missing parameters.
        If parameters are missing, the function will handle asking the user for them.

        If the request is successful, it means the data will be returned.
        The LLM should deliver the data to the user in an easy to interpret manner.

        Returns:
            result (str): The result of the data request.

        Args:
            deviceCategoryCode (str): An ONC-defined code identifying the type of device 
                                    (e.g., DIVE_COMPUTER, NAV, ROV_CAMERA, ACOUSTICRECEIVER, ADCP1200KHZ).
            locationCode (str): An ONC-defined code identifying the location of the device 
                                (e.g., 'CBYDS' for the Cambridge Bay Diver data or 'CBYIP' for the Cambridge Bay Underwater Network or 'CBYSP' for the Cambridge Bay Safe Passage Buoy or 'CBYSS' for the Cambridge Bay Shore Station).
            propertyCode (str): An ONC-defined code identifying the type of data being requested 
                                (e.g., 'oxygen' for oxygen data, 'temperature' for temperature data).
            dateFrom (str): The start date of the data request in ISO 8601 format 
                            (e.g., '2016-06-01T00:00:00.000Z'). (YYYY-MM-DDTHH:MM:SS.sssZ)
            dateTo (str): The end date of the data request in ISO 8601 format 
                          (e.g., '2016-09-30T23:59:59.999Z'). (YYYY-MM-DDTHH:MM:SS.sssZ)
            resamplePeriod (str): The rate at which the data should be sampled 
                                  (e.g., '1' for every second, '3600' for hourly).
            resampleType (str): How the data is sampled 
                                ('avg' for just averages, 'avgMinMax' to get all three of average, minimum and maximum, 'minMax' for minimum and maximum).
    """
    
    if deviceCategoryCode is None and "deviceCategoryCode" in obtainedParams:
        deviceCategoryCode = obtainedParams.get("deviceCategoryCode")
    if locationCode is None and "locationCode" in obtainedParams:
        locationCode = obtainedParams.get("locationCode")
    if propertyCode is None and "propertyCode" in obtainedParams:
        propertyCode = obtainedParams.get("propertyCode")
    if resamplePeriod is None and "resamplePeriod" in obtainedParams:
        resamplePeriod = obtainedParams.get("resamplePeriod")
    if resampleType is None and "resampleType" in obtainedParams:
        resampleType = obtainedParams.get("resampleType")
    if dateFrom is None and "dateFrom" in obtainedParams:
        dateFrom = obtainedParams.get("dateFrom")
    if dateTo is None and "dateTo" in obtainedParams:
        dateTo = obtainedParams.get("dateTo")
    allParams = {
        "deviceCategoryCode": deviceCategoryCode, 
        "propertyCode": propertyCode, 
        "resamplePeriod": resamplePeriod, 
        "resampleType": resampleType, 
        "locationCode": locationCode, 
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
            "status": StatusCode.PARAMS_NEEDED,
            "response": f"Hey! It looks like you're requesting data! So far I have the following parameters: {', '.join(obtainedParams.keys())}. However, I still need you to please provide the following missing parameters so I can complete the data request: {', '.join(neededParams)}. Thank you!",
            "obtainedParams": obtainedParams,
        }
    params = {
        "deviceCategoryCode": deviceCategoryCode, 
        "propertyCode": propertyCode, 
        "resamplePeriod": resamplePeriod, 
        "resampleType": resampleType, 
        "locationCode": locationCode, 
        "dateFrom": dateFrom, 
        "dateTo": dateTo,
        "dpo_qualityControl": "1", #1 means to clean the data, 0 means to not clean the data. Cleaning the data will use qaqc flags 3,4 and 6 to be replaced with Nans when dpo)dataGaps is set to 1. If its set to 0, then the data will be removed.
        # "dpo_resample": "none",#No sampling done. If set to average, then the data will be averaged over the time period specified. This auto cleans the data. Same for minMax and minMaxAvg.
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
        response = (onc.getScalardata(params))
        print(f"Response from ONC: {response}")
        return response
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        return {
            "status": StatusCode.REQUEST_ERROR,
            "response": "Data is unavailable for this sensor and time.",
        }
