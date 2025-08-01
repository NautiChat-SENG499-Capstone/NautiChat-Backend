import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from onc import ONC

# Load location code from .env (fallback)
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE", "CBY")  # Default to CBY
cambridgeBayLocations = [
    "CBY",
    "CBYDS",
    "CBYIP",
    "CBYIJ",
    "CBYIU",
    "CBYSP",
    "CBYSS",
    "CBYSU",
    "CF240",
]


async def get_daily_sea_temperature_stats_cambridge_bay(
    day_str: str, user_onc_token: str
):
    """
    Get daily sea temperature statistics for Cambridge Bay
    Args:
        day_str (str): Date in YYYY-MM-DD format
        user_onc_token (str): User's ONC token for API access
    """

    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = datetime.strptime(day_str, "%Y-%m-%d") + timedelta(days=1)
    date_to_str: str = date_to.strftime("%Y-%m-%d")  # Convert back to string

    try:
        async with httpx.AsyncClient() as client:
            # Get the data from ONC API
            temp_api = f"https://data.oceannetworks.ca/api/scalardata/location?locationCode={CAMBRIDGE_LOCATION_CODE}&deviceCategoryCode=CTD&propertyCode=seawatertemperature&dateFrom={day_str}&dateTo={date_to_str}&rowLimit=80000&outputFormat=Object&resamplePeriod=86400&token={user_onc_token}"
            response = await client.get(temp_api)
            response.raise_for_status()  # Error handling
            response = response.json()

        if response["sensorData"] is None:
            return {
                "response": "Error: No data available for the given date.",
                "urlParamsUsed": {},
                "baseUrl": temp_api,
            }

        data = response["sensorData"][0]["data"][0]

        # Get min, max, and average and store in dictionary
        return {
            "response": {
                "description": f"Daily sea temperature statistics for Cambridge Bay during day: {day_str}",
                "daily_min": round(data["minimum"], 2),
                "daily_max": round(data["maximum"], 2),
                "daily_avg": round(data["value"], 2),
            },
            "urlParamsUsed": {},
            "baseUrl": temp_api,
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {
                "response": "Error: Invalid ONC token. Please check your token and try again.",
                "urlParamsUsed": {},
                "baseUrl": temp_api,
            }
        elif e.response.status_code == 403:
            return {
                "response": "Error: Access denied. Your ONC token may not have permission for this data.",
                "urlParamsUsed": {},
                "baseUrl": temp_api,
            }
        else:
            return {
                "response": f"Error: API request failed with status {e.response.status_code}",
                "urlParamsUsed": {},
                "baseUrl": temp_api,
            }
    except Exception as e:
        return {
            "response": f"Error: Failed to fetch temperature data: {str(e)}",
            "urlParamsUsed": {},
            "baseUrl": temp_api,
        }


async def get_deployed_devices_over_time_interval(
    dateFrom: str, dateTo: str, user_onc_token: str
):
    """
    Get the devices at cambridge bay deployed over the specified time interval including sublocations
    Args:
        dateFrom (str): ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')
        dateTo (str): ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')
        user_onc_token (str): User's ONC token for API access
    Returns:
        JSON string: List of deployed devices and their metadata Each item includes:
            - begin (str): deployment start time
            - end (str): deployment end time
            - deviceCode (str)
            - deviceCategoryCode (str)
            - locationCode (str)
            - citation (dict): citation metadata (includes description, doi, etc)
    """

    deployedDevices = []
    onc = ONC(user_onc_token)

    for locationCode in cambridgeBayLocations:
        params = {
            "locationCode": locationCode,
            "dateFrom": dateFrom,
            "dateTo": dateTo,
        }
        try:
            response = onc.getDeployments(params)
        except Exception as e:
            if hasattr(e, "response") and e.response.status_code == 404:
                # print(f"Warning: No deployments found for locationCode {locationCode}")
                continue
            elif hasattr(e, "response") and e.response.status_code == 401:
                return {
                    "response": "Error: Invalid ONC token. Please check your token and try again.",
                    "urlParamsUsed": {
                        "locationCode": locationCode,
                        "dateFrom": dateFrom,
                        "dateTo": dateTo,
                        "token": user_onc_token,
                    },
                    "baseUrl": "https://data.oceannetworks.ca/api/deployments?",
                }
            elif hasattr(e, "response") and e.response.status_code == 403:
                return {
                    "response": "Error: Access denied. Your ONC token may not have permission for this data.",
                    "urlParamsUsed": {
                        "locationCode": locationCode,
                        "dateFrom": dateFrom,
                        "dateTo": dateTo,
                        "token": user_onc_token,
                    },
                    "baseUrl": "https://data.oceannetworks.ca/api/deployments?",
                }
            else:
                return {
                    "response": f"Error: Failed to fetch deployment data: {str(e)}",
                    "urlParamsUsed": {
                        "locationCode": locationCode,
                        "dateFrom": dateFrom,
                        "dateTo": dateTo,
                        "token": user_onc_token,
                    },
                    "baseUrl": "https://data.oceannetworks.ca/api/deployments?",
                }

        for deployment in response:
            if deployment is None:
                continue
            device_info = {
                "begin": deployment["begin"],
                "end": deployment["end"],
                "deviceCode": deployment["deviceCode"],
                "deviceCategoryCode": deployment["deviceCategoryCode"],
                "locationCode": deployment["locationCode"],
                "citation": deployment["citation"],
            }
            deployedDevices.append(device_info)

    if deployedDevices == []:
        return {
            "response": "No data available for the given date.",
            "urlParamsUsed": {
                "locationCode": CAMBRIDGE_LOCATION_CODE,
                "dateFrom": dateFrom,
                "dateTo": dateTo,
                "token": user_onc_token,
            },
            "baseUrl": "https://data.oceannetworks.ca/api/deployments?",
        }

    return {
        "response": {
            "deployedDevices": deployedDevices,
            "description": f"Deployed devices at Cambridge Bay over the specified time interval ({dateFrom} to {dateTo}) including sublocations",
        },
        "urlParamsUsed": {
            "locationCode": CAMBRIDGE_LOCATION_CODE,
            "dateFrom": dateFrom,
            "dateTo": dateTo,
            "token": user_onc_token,
        },
        "baseUrl": "https://data.oceannetworks.ca/api/deployments?",
    }


async def get_active_instruments_at_cambridge_bay(user_onc_token: str):
    """
    Get the number of instruments collecting data at Cambridge Bay over the specified interval.
    Uses the ONC Python client to access deployment and stream data.

    Returns:
        JSON string: Dictionary with count and optional metadata.
            {
                "activeInstrumentCount": int,
                "details": [ ... ]
            }
    """

    onc = ONC(user_onc_token)
    active_instruments = []
    deployed_device_count = 0

    for locationCode in cambridgeBayLocations:
        params = {
            "locationCode": locationCode,
        }
        try:
            deployments = onc.getDeployments(params)
        except Exception:
            continue  # Skip any failure silently

        if not deployments:
            continue

        for device in deployments:
            if device.get("end") is not None:
                continue  # deployment is not ongoing
            deployed_device_count = deployed_device_count + 1
            active_instruments.append(device)
    result = {
        "activeInstrumentCount": deployed_device_count,
        "details": active_instruments,
    }
    return {
        "response": {
            "result": result,
            "description": "The number of instruments collecting data at Cambridge Bay and the active instruments",
        },
        "urlParamsUsed": {
            "locationCode": locationCode,
            "token": user_onc_token,
        },
        "baseUrl": "https://data.oceannetworks.ca/api/deployments?",
    }


async def get_time_range_of_available_data(
    deviceCategoryCode: str, user_onc_token: str
):
    """
    Get all deployment time ranges (begin and end times) at Cambridge Bay for a specific device category.
    Returns:
        JSON string: Sorted list of (begin, end) tuples as ISO strings.
    """
    onc = ONC(user_onc_token)
    time_ranges = []

    for locationCode in cambridgeBayLocations:
        params = {
            "locationCode": locationCode,
            "deviceCategoryCode": deviceCategoryCode,
        }
        try:
            deployments = onc.getDeployments(params)
        except Exception:
            continue  # Skip any errors silently

        for device in deployments:
            begin = device.get("begin")
            end = device.get("end")
            if begin:
                time_ranges.append((begin, end))

    time_ranges.sort(key=lambda x: datetime.fromisoformat(x[0].replace("Z", "+00:00")))
    return {
        "response": time_ranges,
        "urlParamsUsed": {
            "deviceCategoryCode": deviceCategoryCode,
            "token": user_onc_token,
            "locationCodes": cambridgeBayLocations,
        },
        "baseUrl": "https://data.oceannetworks.ca/api/deployments?",
    }
