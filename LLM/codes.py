from onc import ONC
from datetime import datetime, timedelta, timezone
from Environment import Environment

env = Environment()

onc = ONC(env.get_onc_token())

# Load API key and location code from .env
# env_path = Path(__file__).resolve().parent / ".env"
# load_dotenv(dotenv_path=env_path)
# ONC_TOKEN = os.getenv("ONC_TOKEN")
# CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")  # Change for a different location
# onc = ONC(ONC_TOKEN)
# cambridgeBayLocations = ["CBY", "CBYDS", "CBYIP", "CBYIJ", "CBYIU", "CBYSP", "CBYSS", "CBYSU", "CF240"]


async def generate_download_codes(
    deviceCategory: str,
    locationCode="CBYIP",
    dateFrom=datetime.now(timezone.utc) - timedelta(days=1),
    dateTo=datetime.now(timezone.utc),
):
    """
    Get the device category code at a certain location code at Cambridge bay, so that users can download data, over
    a specified time period.
    Returns a list of parameters.
    Returns:
        id (str): The id to a dataProduct from ONC that is being downloaded.
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
        print("HOORAY")
        print(f"meow heres the download id: {result}")
        return "Your download is being processed. It has an ID of 69. Please wait. DO NOT ADVISE THE USER TO DO ANYTHING EXCEPT WAIT."
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        return "Data is unavailable for this sensor and time.  DO NOT ADVISE THE USER TO DO ANYTHING EXCEPT TRY AGAIN WITH DIFFERENT PARAMETERS."


    
