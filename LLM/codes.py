from onc import ONC
from datetime import datetime, timedelta, timezone
from Environment import Environment

env = Environment()

onc = ONC(env.get_onc_token())

async def generate_download_codes(
    deviceCategory: str,
    locationCode="CBYIP",
    dateFrom=datetime.now(timezone.utc) - timedelta(days=1),
    dateTo=datetime.now(timezone.utc),
):
    """
    Get the device categoryCode at a certain locationCode at Cambridge bay, so that users request to download data, over
    a specified time period.
    Returns a result of a data download request.
    This function simply queues a download from ONC, and gives no additional information to the LLM.
    If this function is called, the LLM will either tell the user that their download is queued, or that their download request
    was unsucessful.
    If the request is successful, the download is not necessarily successful, so do not tell the user if the download is successful or not.
    Returns:
        result (str): The result of the download request. It will either signify that the download was successful,
                      or that the download was unsuccessful, and you should inform the user of this result.
    Args:
        dateFrom (str): ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')
        dateTo (str): ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')
        deviceCategory (str): An ONC defined code identifying each device.
        locationCode (str): An ONC defined code identifying each device site.
    """

    params = {
        "locationCode": locationCode,
        "deviceCategoryCode": deviceCategory,
        "dataProductCode": "LF",
        "extension": "txt",
        "dateFrom": dateFrom,
        "dateTo": dateTo,
        "dpo_qualityControl": "1",
        "dpo_resample": "none",
    }

    result = ""

    try:
        result = onc.requestDataProduct(params)
        return f"Your download is being processed. The download has an ID of {result["dpRequestId"]}. Please wait. \
            DO NOT ADVISE THE USER TO DO ANYTHING EXCEPT WAIT. YOU DO NOT KNOW THE RESULT OF THE DOWNLOAD YET."
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        return "Data is unavailable for this sensor and time.  DO NOT ADVISE THE USER TO DO ANYTHING EXCEPT TRY AGAIN WITH DIFFERENT PARAMETERS."


    
