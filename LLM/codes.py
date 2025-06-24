from onc import ONC
from datetime import datetime, timedelta, timezone
from Environment import Environment

env = Environment()

onc = ONC(env.get_onc_token())


async def generate_download_codes(
    deviceCategory: str,
    locationCode: str,
    dataProductCode: str,
    extension: str,
    dateFrom: str,
    dateTo: str,
):
    from LLM import set_request_id, get_request_id

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

    params = {
        "locationCode": locationCode,
        "deviceCategoryCode": deviceCategory,
        "dataProductCode": dataProductCode,
        "extension": extension,
        "dateFrom": dateFrom,
        "dateTo": dateTo,
        "dpo_qualityControl": "1",
        "dpo_resample": "none",
        "dpo_dataGaps": "1",
    }

    try:
        set_request_id(onc.requestDataProduct(params))
        return {
            "status": "queued",
            "dpRequestId": get_request_id(),
            "message": "Your download is being processed. "
            "Please wait. DO NOT ADVISE THE USER TO DO ANYTHING EXCEPT WAIT.",
        }
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "message": "Data is unavailable for this sensor and time. "
            "DO NOT ADVISE THE USER TO DO ANYTHING EXCEPT TRY AGAIN WITH DIFFERENT PARAMETERS.",
        }
