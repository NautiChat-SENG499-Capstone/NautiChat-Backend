from datetime import datetime, timedelta
from typing import Dict

from onc import ONC

from LLM.Constants.status_codes import StatusCode
from LLM.schemas import ObtainedParamsDictionary


# What was the air temperature in Cambridge Bay on this day last year?
async def get_daily_air_temperature_stats_cambridge_bay(
    date_from_str: str, user_onc_token: str
):
    """
    Get daily air temperature statistics for Cambridge Bay.
    Args:
        date_from_str (str): Date in YYYY-MM-DD format
    Returns:
        JSON string containing:
          {
            "date": "2024-06-23",
            "min": 3.49,
            "max": 6.54,
            "average": 5.21,
            "samples": 1440
          }
    """
    onc = ONC(user_onc_token)

    # Build 24-hour window
    date_to_str = (
        datetime.strptime(date_from_str, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    params = {
        "locationCode": "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "dateFrom": date_from_str,
        "dateTo": date_to_str,
    }

    data = onc.getScalardataByLocation(params)
    sensorData = data.get("sensorData", [])
    if not sensorData:
        return {
            "response": {
                "stats": {
                    "date": date_from_str,
                    "min_temp": None,
                    "max_temp": None,
                    "mean": None,
                    "samples": 0,
                },
                "description": f"Air temperature statistics for Cambridge Bay on day: {date_from_str} don't exist",
            },
            "urlParamsUsed": {
                "locationCode": "CBYSS.M2",
                "deviceCategoryCode": "METSTN",
                "dateFrom": date_from_str,
                "dateTo": date_to_str,
                "token": user_onc_token,
            },
            "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
        }
    temps = sensorData[0]["data"]["values"]
    mean = sum(temps) / len(temps)
    max_temp = max(temps)
    min_temp = min(temps)
    stats = {
        "date": date_from_str,
        "min_temp": min_temp,
        "max_temp": max_temp,
        "mean": mean,
        "samples": len(temps),
    }
    # print(stats)
    return {
        "response": {
            "stats": stats,
            "description": f"Air temperature statistics for Cambridge Bay on day: {date_from_str}",
        },
        "urlParamsUsed": {
            "locationCode": "CBYSS.M2",
            "deviceCategoryCode": "METSTN",
            "dateFrom": date_from_str,
            "dateTo": date_to_str,
            "token": user_onc_token,
        },
        "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
    }


# Can you give me an example of 24 hours of oxygen data?
async def get_oxygen_data_24h(
    user_onc_token: str, date_from_str: str = "2024-06-24"
):  # Date guaranteed to have data
    """
    Get 24 hours of dissolved oxygen data for Cambridge Bay.
    Args:
        date_from_str (str): Date in YYYY-MM-DD format
    Returns:
        pandas DataFrame with datetime + oxygen_ml_per_l columns,
        sampled at 10 minute intervals.
    """
    onc = ONC(user_onc_token)

    # Build 24-hour window
    date_to_str = (
        datetime.strptime(date_from_str, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    params = {
        "locationCode": "CBYIP",
        "deviceCategoryCode": "OXYSENSOR",
        "propertyCode": "oxygen",
        "dateFrom": date_from_str,
        "dateTo": date_to_str,
        # "metadata":           "Full", #If want metadata
        "resamplePeriod": 3600,  # In one hour intervals
    }

    # Fetch raw JSON
    raw = onc.getScalardata(params)

    # Pick the first sensor (usually the “corrected” series)
    sensorData = raw["sensorData"]
    if not sensorData:
        return {
            "response": "Error: No oxygen data available for the given date.",
            "urlParamsUsed": {
                "locationCode": "CBYIP",
                "deviceCategoryCode": "OXYSENSOR",
                "propertyCode": "oxygen",
                "dateFrom": date_from_str,
                "dateTo": date_to_str,
                "resamplePeriod": "3600",
                "token": user_onc_token,
            },
            "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
        }
    sensor = sensorData[0]["data"]
    times = sensor["sampleTimes"]
    values = sensor["values"]

    # Build DataFrame
    oxygenData = {"datetime": times, "oxygen_ml_per_l": values}
    # print(oxygenData)
    return {
        "response": {
            "oxygenData": oxygenData,
            "description": f"24 hours of dissolved oxygen data for Cambridge Bay on day: {date_from_str}",
        },
        "urlParamsUsed": {
            "locationCode": "CBYSS.M2",
            "deviceCategoryCode": "METSTN",
            "dateFrom": date_from_str,
            "dateTo": date_to_str,
            "token": user_onc_token,
        },
        "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
    }


# I’m interested in data on ship noise for July 31, 2024 / Get me the acoustic data for the last day in July of 2024
async def get_ship_noise_acoustic_for_date(
    date_from_str: str, user_onc_token: str
) -> dict:
    """
    Submit a request to ONC's API for 24 hours of ship noise acoustic data (WAV format)
    from Cambridge Bay. Returns request metadata and status.

    Args:
        date_from_str (str): Start date in YYYY‑MM‑DD format
        user_onc_token (str): ONC API token

    Returns:
        dict: {
            "status": int,
            "response": { ... },
            "urlParamsUsed": { ... },
            "baseUrl": "...",
        }
        or error:
        {
            "status": int,
            "error": str,
            "urlParamsUsed": { ... },
            "baseUrl": "...",
        }
    """
    onc = ONC(user_onc_token)

    # Build 24-hour window
    date_to_str = (
        datetime.strptime(date_from_str, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    params = {
        "dataProductCode": "AD",  # Acoustic Data
        "extension": "wav",
        "dateFrom": date_from_str,
        "dateTo": date_to_str,
        "locationCode": "CBYIP",
        "deviceCategoryCode": "HYDROPHONE",
        "dpo_audioDownsample": -1,  # Keep original sampling rate
        "dpo_audioFormatConversion": 0,  # Skip reprocessing if already archived
    }

    params["token"] = user_onc_token  # Add the ONC token to the parameters.

    try:
        # Submit data product order to ONC
        order = onc.requestDataProduct(params)

        # Try to extract request ID, DOI, etc. if present
        dpRequestId = order["dpRequestId"]
        doi = order["citations"][0]["doi"] if order else "No DOI available"
        citation = (
            order["citations"][0]["citation"] if order else "No citation available"
        )

        return {
            "status": StatusCode.PROCESSING_DATA_DOWNLOAD,
            "dpRequestId": dpRequestId,
            "doi": doi,
            "citation": citation,
            "response": (
                f"Ship noise .wav file order successfully queued for Cambridge Bay "
                f"from {date_from_str} to {date_to_str}."
            ),
            "urlParamsUsed": params,
            "baseUrl": "https://data.oceannetworks.ca/api/hydrophone/requestDataProduct?",
            "obtainedParams": ObtainedParamsDictionary(
                **params
            ),  # Structured as a Pydantic model
        }

    except Exception as e:
        print(
            f"{type(e).__name__} occurred while submitting noise acoustic data request: {e}"
        )
        return {
            "status": StatusCode.ERROR_WITH_DATA_DOWNLOAD,
            "response": "An error occurred while submitting your noise acoustic data request.",
            "obtainedParams": ObtainedParamsDictionary(**params),
            "urlParamsUsed": params,
            "baseUrl": "https://data.oceannetworks.ca/api/hydrophone/requestDataProduct?",
        }


# Can I see the noise data for July 31, 2024 as a spectogram?
async def plot_spectrogram_for_date(date_str: str, user_onc_token: str) -> Dict:
    """
    Submit a request to Ocean Networks Canada's dataProductDelivery API for a
    ship noise spectrogram image from the Cambridge Bay hydrophone for a given date.

    This function requests the pre-generated spectrogram (PNG format) covering a
    24-hour period and returns metadata about the request. This does not return the actual
    image but returns a reference to the order request.

    Args:
        date_str (str): Date of interest in YYYY-MM-DD format.
        user_onc_token (str): ONC API access token.

    Returns:
        dict: A dictionary containing status, response, and metadata.
    """
    onc = ONC(user_onc_token)

    # Build 24-hour window
    date_from = date_str
    date_to = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )

    params = {
        "dataProductCode": "HSD",  # Hydrophone Spectrogram Data
        "extension": "png",
        "dateFrom": date_from,
        "dateTo": date_to,
        "locationCode": "CBYIP",
        "deviceCategoryCode": "HYDROPHONE",
    }

    params["token"] = user_onc_token  # Add the ONC token to the parameters.

    try:
        # Submit data product order to ONC
        order = onc.requestDataProduct(params)

        # Try to extract request ID, DOI, etc. if present
        print(order)
        dpRequestId = order["dpRequestId"]
        doi = order["citations"][0]["doi"] if order else "No DOI available"
        citation = (
            order["citations"][0]["citation"] if order else "No citation available"
        )

        return {
            "status": StatusCode.PROCESSING_DATA_DOWNLOAD,
            "dpRequestId": dpRequestId,
            "doi": doi,
            "citation": citation,
            "response": (
                f"Ship noise spectrogram order successfully queued for Cambridge Bay "
                f"from {date_from} to {date_to}."
            ),
            "urlParamsUsed": params,
            "baseUrl": "https://data.oceannetworks.ca/api/hydrophone/requestDataProduct?",
            "obtainedParams": ObtainedParamsDictionary(
                **params
            ),  # Structured as a Pydantic model
        }

    except Exception as e:
        print(f"{type(e).__name__} occurred while submitting spectrogram request: {e}")
        return {
            "status": StatusCode.ERROR_WITH_DATA_DOWNLOAD,
            "response": "An error occurred while submitting your spectrogram data request.",
            "obtainedParams": ObtainedParamsDictionary(**params),
            "urlParamsUsed": params,
            "baseUrl": "https://data.oceannetworks.ca/api/hydrophone/requestDataProduct?",
        }


# How windy was it at noon on March 1 in Cambridge Bay?
async def get_wind_speed_at_timestamp(
    date_from_str: str, user_onc_token: str, hourInterval: int = 12
):
    """
    Get wind speed at Cambridge Bay (in m/s) at the specified timestamp.
    Args:
        date_from_str (str): Date to get wind speed in YYYY-MM-DD format, (e.g. \"2024-06-23\").
        hourInterval (int): Hour interval to find the wind speed, default is 12 (noon)
    Returns:
        float: windspeed at that time (in m/s), or the nearest sample.
    """
    onc = ONC(user_onc_token)

    # Parse into datetime and get the date
    date_time_date_from_str = datetime.strptime(date_from_str, "%Y-%m-%d")
    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = date_time_date_from_str + timedelta(days=1)
    date_to_str = date_to.strftime("%Y-%m-%d")  # Convert back to string
    time_to_find = date_time_date_from_str + timedelta(
        hours=hourInterval, minutes=0, seconds=0
    )
    time_to_find_str = time_to_find.strftime("%Y-%m-%dT%H:%M:%SZ")
    # print(date_from_str, date_to_str, time_to_find)
    # Fetch relevant data through API request
    params = {
        "locationCode": "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "propertyCode": "windspeed",
        "dateFrom": date_from_str,
        "dateTo": date_to_str,
    }
    raw = onc.getScalardata(params)
    sensorData = raw["sensorData"]
    if not sensorData:
        return {
            "response": {
                "result": {
                    "datetime": time_to_find.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "wind_speed_m_s": None,
                },
                "description": f"Wind speed at Cambridge Bay (in m/s) at the specified timestamp: {time_to_find_str} don't exist",
            },
            "urlParamsUsed": {
                "locationCode": "CBYSS.M2",
                "deviceCategoryCode": "METSTN",
                "propertyCode": "windspeed",
                "dateFrom": date_from_str,
                "dateTo": date_to_str,
                "token": user_onc_token,
            },
            "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
        }

    block = sensorData[0]["data"]
    threshold = timedelta(seconds=30)
    matching_indices = [
        i
        for i, ts in enumerate(block["sampleTimes"])
        if abs(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ") - time_to_find)
        <= threshold
    ]
    wind_speed_at_time = (
        block["values"][matching_indices[0]] if matching_indices else None
    )
    data = {
        "datetime": time_to_find_str,
        "wind_speed_m_s": wind_speed_at_time,
    }
    # print(data)
    return {
        "response": {
            "data": data,
            "description": f"Wind speed at Cambridge Bay (in m/s) at the specified timestamp: {time_to_find_str}",
        },
        "urlParamsUsed": {
            "locationCode": "CBYSS.M2",
            "deviceCategoryCode": "METSTN",
            "propertyCode": "windspeed",
            "dateFrom": date_from_str,
            "dateTo": date_to_str,
            "token": user_onc_token,
        },
        "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
    }


# How thick was the ice in February this year?
async def get_ice_thickness(date_from_str: str, date_to_str: str, user_onc_token: str):
    """
    Get sea-ice thickness for a range of time in Cambridge Bay.
    Args:
        date_from_str (str): Date in YYYY-MM-DD format
    Returns:
        JSON string of the scalar data response
    """
    onc = ONC(user_onc_token)

    # Include the full end_date by adding one day (API dateTo is exclusive)
    # date_to_str = (
    #     datetime.strptime(date_from_str, "%Y-%m-%d")
    #     + timedelta(month=1)
    # ).strftime("%Y-%m-%d")
    if date_from_str == date_to_str:  # One day interval
        date_to_str = (
            datetime.strptime(date_from_str, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")

    params = {
        "locationCode": "CBYIP",
        "deviceCategoryCode": "ICEPROFILER",
        "sensorCategoryCodes": "ice_thickness_corrected",
        "dateFrom": date_from_str,
        "dateTo": date_to_str,
    }

    # Fetch all records in the range
    response = onc.getScalardata(params)
    records = response["sensorData"]
    if not records:
        return {
            "response": {
                "average_ice_thickness": -1,
                "description": f"Average Sea-ice thickness in meters for over the time range: {date_from_str} to {date_to_str} don't exist",
            },
            "urlParamsUsed": {
                "locationCode": "CBYIP",
                "deviceCategoryCode": "ICEPROFILER",
                "sensorCategoryCodes": "ice_thickness_corrected",
                "dateFrom": date_from_str,
                "dateTo": date_to_str,
                "token": user_onc_token,
            },
            "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
        }  # No data available for the given date
    values = records[0]["data"]["values"]
    flags = records[0]["data"]["qaqcFlags"]
    data = [
        val
        for index, val in enumerate(values)
        if (val is not None and flags[index] < 3)
    ]
    average_ice_thickness = sum(data) / len(data) if data else None
    # Return the average of those daily means
    # print(f"Average ice thickness from {date_from_str} to {date_to_str}: {average_ice_thickness} m")
    return {
        "response": {
            "average_ice_thickness": round(average_ice_thickness, 3),
            "description": f"Average Sea-ice thickness in meters for over the time range: {date_from_str} to {date_to_str} is {average_ice_thickness} m",
        },
        "urlParamsUsed": {
            "locationCode": "CBYIP",
            "deviceCategoryCode": "ICEPROFILER",
            "sensorCategoryCodes": "ice_thickness_corrected",
            "dateFrom": date_from_str,
            "dateTo": date_to_str,
            "token": user_onc_token,
        },
        "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
    }
