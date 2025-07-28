from typing import Optional

from onc import ONC

from LLM.Constants.dataDownloadCodes import dataDownloadCodes
from LLM.Constants.status_codes import StatusCode
from LLM.Constants.utils import sync_param
from LLM.schemas import ObtainedParamsDictionary


def obtain_location_codes(deviceCategoryCode: str) -> list[str]:
    locationCodes = []
    for device in dataDownloadCodes:
        if device["deviceCategoryCode"] == deviceCategoryCode:
            locationCodes.append(device["locationCode"])
    return locationCodes


def obtain_data_product_code(extension: str, deviceCategoryCode: str):
    for device in dataDownloadCodes:
        if device["deviceCategoryCode"] == deviceCategoryCode:
            for product in device["possibleDataProducts"]:
                if extension in product["availableExtensions"]:
                    return product["dataProductCode"]
    return None


def find_possible_extensions(deviceCategoryCode: str):
    possibleDataProducts = []
    for device in dataDownloadCodes:
        if device["deviceCategoryCode"] == deviceCategoryCode:
            for product in device["possibleDataProducts"]:
                possibleDataProducts.append(
                    {
                        "dataProduct": product["dataProduct"],
                        "dataProductCode": product["dataProductCode"],
                        "extension": product["availableExtensions"],
                    }
                )

    if len(possibleDataProducts) > 0:
        product_info_list = [
            f"{dataProduct['dataProduct']} ({dataProduct['dataProductCode']}): {', '.join(dataProduct['extension'])}"
            for dataProduct in possibleDataProducts
        ]
        products_str = "; ".join(product_info_list)
        return products_str
    return None


async def generate_download_codes(
    user_onc_token: str,
    deviceCategoryCode: Optional[str] = None,
    locationCode: Optional[str] = None,
    # dataProductCode: Optional[str] = None,
    extension: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    dpo_qualityControl: Optional[int] = 1,
    dpo_dataGaps: Optional[int] = 1,
    dpo_resample: Optional[str] = "none",
    dpo_minMax: Optional[int] = None,
    dpo_average: Optional[int] = None,
    dpo_minMaxAvg: Optional[int] = None,
    obtainedParams: ObtainedParamsDictionary = ObtainedParamsDictionary(),
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
            dpo_qualityControl (bool): Whether to apply quality control to the data. Default is False.
            dpo_dataGaps (bool): Whether to include data gaps in the data. Default is True
            dpo_resample (str): The resampling method to apply to the data. Default is 'none'.
            dpo_minMax (int): Whether to apply min/max resampling. Default is 0 (no min/max).
            dpo_average (int): Whether to apply average resampling. Default is 0 (no average).
            dpo_minMaxAvg (int): Whether to apply min/max and average resampling. Default is 0 (no min/max and average).
            obtainedParams (ObtainedParamsDictionary): A dictionary of parameters that have already been obtained from the user.
    """

    """
        NOTE: data download only actually requires the following parameters:
        dataProductCode, extension, dateFrom, dateTo. Want locationCode as well!
        Acceptable dates/times conform to the ISO 8601 standard.
        The rest are optional.
        Can create URL by appending each paramater to the base URL:
        https://data.oceannetworks.ca/api/dataProductDelivery/request?dataProductCode=
        add dataProductCode first then do ex:
        + "&extension=" + extension
        + "&dateFrom=" + dateFrom
        + "&dateTo=" + dateTo 
        Dont forget to append ONC token at the end of the URL
    """
    allObtainedParams = {}  # List of all parameters that are set.
    deviceCategoryCode = sync_param(
        "deviceCategoryCode", deviceCategoryCode, obtainedParams, allObtainedParams
    )
    locationCode = sync_param(
        "locationCode", locationCode, obtainedParams, allObtainedParams
    )
    extension = sync_param("extension", extension, obtainedParams, allObtainedParams)

    if extension is None:
        obtainedParams.dataProductCode = None
    dataProductCode = obtainedParams.dataProductCode

    if (
        extension is not None and deviceCategoryCode is not None
    ):  # and dataProductCode is None
        dataProductCode = obtain_data_product_code(extension, deviceCategoryCode)
        dataProductCode = sync_param(
            "dataProductCode", dataProductCode, obtainedParams, allObtainedParams
        )
        if dataProductCode is None:
            return {
                "status": StatusCode.ERROR_WITH_DATA_DOWNLOAD,
                "response": f"Error: No data product code found for extension '{extension}' and device category code '{deviceCategoryCode}'.",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            }
    if locationCode is None and deviceCategoryCode is not None:
        locationCodes = obtain_location_codes(deviceCategoryCode)
        if len(locationCodes) == 0:
            return {
                "status": StatusCode.ERROR_WITH_DATA_DOWNLOAD,
                "response": f"Error: No location codes found for device category code '{deviceCategoryCode}'. Please select a different device category code or check the available location codes.",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            }
        elif len(locationCodes) == 1:
            locationCode = locationCodes[0]
            locationCode = sync_param(
                "locationCode", locationCode, obtainedParams, allObtainedParams
            )
        else:  # If there are multiple location codes, return them to the user
            return {
                "status": StatusCode.PARAMS_NEEDED,
                "response": f"Hey! It looks like you want to do a data download! However, I found multiple location codes for device category code '{deviceCategoryCode}': {', '.join(locationCodes)}. Please specify which one you want to use.",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            }

    dateFrom = sync_param("dateFrom", dateFrom, obtainedParams, allObtainedParams)
    dateTo = sync_param("dateTo", dateTo, obtainedParams, allObtainedParams)
    #  "dpo_qualityControl": "1", #1 means to clean the data, 0 means to not clean the data. Cleaning the data will use qaqc flags 3,4 and 6 to be replaced with Nans when dpo)dataGaps is set to 1. If its set to 0, then the data will be removed.
    #  "dpo_resample": "none",#No sampling done. If set to average, then the data will be averaged over the time period specified. This auto cleans the data. Same for minMax and minMaxAvg.
    #  #If using dpo_resample then can use for example dpo_minMaxAvg = {0, 60, 600, 900, 3600, 86400} to get 1 min, 10 min, 10 min, 15 min, 1 hour, and 1 day min, max and averages.
    #  "dpo_dataGaps": "1", #Fills missing/bad data with NaNs
    dpo_dataGaps = sync_param(
        "dpo_dataGaps", dpo_dataGaps, obtainedParams, allObtainedParams
    )
    dpo_resample = sync_param(
        "dpo_resample", dpo_resample, obtainedParams, allObtainedParams
    )
    if dpo_resample in ["average"]:
        dpo_qualityControl = 1  # If resampling is done for just average, then quality control must be applied by default.

    dpo_qualityControl = sync_param(
        "dpo_qualityControl", dpo_qualityControl, obtainedParams, allObtainedParams
    )
    dpo_minMax = sync_param("dpo_minMax", dpo_minMax, obtainedParams, allObtainedParams)
    dpo_average = sync_param(
        "dpo_average", dpo_average, obtainedParams, allObtainedParams
    )
    dpo_minMaxAvg = sync_param(
        "dpo_minMaxAvg", dpo_minMaxAvg, obtainedParams, allObtainedParams
    )
    print(f"Obtained parameters: {allObtainedParams}")
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

    allParamsNeeded = {
        "dataProductCode": dataProductCode,
        "extension": extension,
        "dateFrom": dateFrom,
        "dateTo": dateTo,
        "locationCode": locationCode,
    }  # Only the necessary parameters for a data download request.
    neededParams = [
        param for param, value in allParamsNeeded.items() if value is None
    ]  # List of paramaters that are needed but not set.

    if len(neededParams) > 0:  # If need one or more parameters
        print("OBTAINED PARAMS: ", ObtainedParamsDictionary(**allObtainedParams))
        if extension is None and deviceCategoryCode is not None:
            possibleExtensionStr = find_possible_extensions(deviceCategoryCode)
            if possibleExtensionStr:
                return {
                    "status": StatusCode.PARAMS_NEEDED,
                    "response": (
                        f"Hey! It looks like you want to do a data download! So far I have the following parameters: "
                        f"{', '.join(allObtainedParams.keys())}. "
                        f"However, I still need you to please provide the following missing parameters so I can complete the data download request: {', '.join(neededParams)}. "
                        f"Some possible extensions for data download are also as follows: {possibleExtensionStr}. "
                        f"Thank you!"
                    ),
                    "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
                }

        return {
            "status": StatusCode.PARAMS_NEEDED,
            "response": f"Hey! It looks like you want to do a data download! So far I have the following parameters: {', '.join(allObtainedParams.keys())}. However, I still need you to please provide the following missing parameters so I can complete the data download request: {', '.join(neededParams)}. Thank you!",
            "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
        }

    try:
        response = onc.requestDataProduct(allObtainedParams)
        print(f"Response from ONC: {response}")
        return {
            "status": StatusCode.PROCESSING_DATA_DOWNLOAD,
            "dpRequestId": response["dpRequestId"],
            "doi": response["citations"][0]["doi"],
            "citation": response["citations"][0]["citation"],
            "response": "Your download is being processed. Is there anything else I can help you with?",
            "urlParamsUsed": allObtainedParams,
            "baseUrl": "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
        }
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        return {
            "status": StatusCode.ERROR_WITH_DATA_DOWNLOAD,
            "response": "Either Data is unavailable for this sensor and time or there was an error with your request.",  # can switch to just return the error message if we want to be more specific.
            "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            "urlParamsUsed": allObtainedParams,
            "baseUrl": "https://data.oceannetworks.ca/api/dataProductDelivery/request?",
        }
