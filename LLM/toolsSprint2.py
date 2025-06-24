from onc import ONC
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv
from pathlib import Path

# Load API key and location code from .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")  # Change for a different location
cambridgeBayLocations = ["CBY", "CBYDS", "CBYIP", "CBYIJ", "CBYIU", "CBYSP", "CBYSS", "CBYSU", "CF240"]

# Create ONC object
onc = ONC(ONC_TOKEN)


# What was the air temperature in Cambridge Bay on this day last year?
async def get_daily_air_temperature_stats_cambridge_bay(date_from_str: str):
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
    # Build 24-hour window
    date_to_str = (
        datetime.strptime(date_from_str, "%Y-%m-%d")
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    params = {
        "locationCode": "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "dateFrom":           date_from_str,
        "dateTo":             date_to_str,
    }

    data = onc.getScalardata(params)
    sensorData = data.get("sensorData", [])
    if not sensorData:
        return {
            "date": date_from_str,
            "min_temp": None,
            "max_temp": None,
            "mean": None,
            "samples": 0
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
    #print(stats)
    return stats


# Can you give me an example of 24 hours of oxygen data?
async def get_oxygen_data_24h(date_from_str: str = "2024-06-24"):#Date guaranteed to have data
    """
    Get 24 hours of dissolved oxygen data for Cambridge Bay.
    Args:
        date_from_str (str): Date in YYYY-MM-DD format
    Returns:
        pandas DataFrame with datetime + oxygen_ml_per_l columns,
        sampled at 10 minute intervals.
    """
    # Build 24-hour window
    
    date_to_str = (
        datetime.strptime(date_from_str, "%Y-%m-%d")
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    params = {
        "locationCode":         "CBYIP",
        "deviceCategoryCode":   "OXYSENSOR",
        "propertyCode":         "oxygen",
        "dateFrom":             date_from_str,
        "dateTo":               date_to_str,
        #"metadata":           "Full", #If want metadata
        "resamplePeriod":       3600,        # In one hour intervals
    }

    # Fetch raw JSON
    raw = onc.getScalardata(params)

    # Pick the first sensor (usually the “corrected” series)
    sensorData = raw["sensorData"]
    if not sensorData:
        return {"datetime": [], "oxygen_ml_per_l": []}
    sensor = sensorData[0]["data"]
    times = sensor["sampleTimes"]
    values = sensor["values"]

    # Build DataFrame
    oxygenData ={
        "datetime": times,
        "oxygen_ml_per_l": values
    }
    #print(oxygenData)
    return oxygenData


# I’m interested in data on ship noise for July 31, 2024 / Get me the acoustic data for the last day in July of 2024
async def get_ship_noise_acoustic_for_date(day_str: str):
    """
    Get 24 hours of ship noise data for Cambridge Bay on a specific date.
    Args:
        day_str (str): Date in YYYY-MM-DD format
    Returns:
        JSON string of the scalar data response
    """
    # Define 24 hour window
    date_from_str = day_str
    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = datetime.strptime(date_from_str, "%Y-%m-%d") + timedelta(days = 1)
    date_to_str = date_to.strftime("%Y-%m-%d")  # Convert back to string

    # Fetch relevant data through API request
    params = {
        "locationCode": {CAMBRIDGE_LOCATION_CODE},
        "deviceCategoryCode": "HYDROPHONE",
        "propertyCode": "voltage",
        "dateFrom": {date_from_str},
        "dateTo": {date_to_str},
        "rowLimit": 250,
        "token": {ONC_TOKEN}
    }
    data = onc.getScalardata(params)

    return data


# Can I see the noise data for July 31, 2024 as a spectogram?
# TO DO data download


# How windy was it at noon on March 1 in Cambridge Bay?
async def get_wind_speed_at_timestamp(date_from_str: str, hourInterval: int = 12):
    """
    Get wind speed at Cambridge Bay (in m/s) at the specified timestamp.
    Args:
        date_from_str (str): Date to get wind speed in YYYY-MM-DD format, (e.g. \"2024-06-23\").
        hourInterval (int): Hour interval to find the wind speed, default is 12 (noon)
    Returns:
        float: windspeed at that time (in m/s), or the nearest sample.
    """
    # Parse into datetime and get the date
    date_time_date_from_str = datetime.strptime(date_from_str, "%Y-%m-%d")
    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = date_time_date_from_str + timedelta(days = 1)
    date_to_str = date_to.strftime("%Y-%m-%d")  # Convert back to string
    time_to_find =  (date_time_date_from_str
                + timedelta(hours=hourInterval, minutes=0, seconds=0)
            )
    #print(date_from_str, date_to_str, time_to_find)
    # Fetch relevant data through API request
    params = {
        "locationCode":       "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "propertyCode":       "windspeed",
        "dateFrom":           date_from_str,
        "dateTo":             date_to_str,     
    }
    raw = onc.getScalardata(params)
    sensorData = raw["sensorData"]
    if not sensorData:
        return {
            "datetime": time_to_find.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "wind_speed_m_s": None
        }
    
    block = sensorData[0]["data"]
    threshold = timedelta(seconds=30)
    matching_indices = [
        i for i, ts in enumerate(block["sampleTimes"])
        if abs(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ") - time_to_find) <= threshold
    ]
    wind_speed_at_time = block["values"][matching_indices[0]] if matching_indices else None
    data = {
        "datetime": time_to_find.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "wind_speed_m_s": wind_speed_at_time
    }
    #print(data)
    return data
    

# I’m doing a school project on Arctic fish. Does the platform have any underwater
# imagery and could I see an example?
# TO DO data download


# How thick was the ice in February this year?
async def get_ice_thickness(date_from_str: str, date_to_str: str):
    """
    Get sea-ice thickness for a range of time in Cambridge Bay.
    Args:
        date_from_str (str): Date in YYYY-MM-DD format
    Returns:
        JSON string of the scalar data response
    """
    # Include the full end_date by adding one day (API dateTo is exclusive)
    # date_to_str = (
    #     datetime.strptime(date_from_str, "%Y-%m-%d")
    #     + timedelta(month=1)
    # ).strftime("%Y-%m-%d")
    if (date_from_str == date_to_str): # One day interval
        date_to_str = (
            datetime.strptime(date_from_str, "%Y-%m-%d")
            + timedelta(days=1)
        ).strftime("%Y-%m-%d")
    params = {
        "locationCode": "CBYIP",
        "deviceCategoryCode": "ICEPROFILER",
        "sensorCategoryCodes": "ice_thickness_corrected",
        "dateFrom": {date_from_str},
        "dateTo": {date_to_str},
    }

    # Fetch all records in the range
    response = onc.getScalardata(params)
    records = response["sensorData"]
    if not records:
        return {"average_ice_thickness": -1}  # No data available for the given date
    values = records[0]["data"]["values"]
    flags = records[0]["data"]["qaqcFlags"]
    data = [val for index, val in enumerate(values) if (val is not None and flags[index] <3)]
    average_ice_thickness = sum(data) / len(data) if data else None
    # Return the average of those daily means
    #print(f"Average ice thickness from {date_from_str} to {date_to_str}: {average_ice_thickness} m")
    return f"Average ice thickness from {date_from_str} to {date_to_str}: {average_ice_thickness} m"


# I would like a plot which shows the water depth so I can get an idea of tides in the Arctic for July 2023
# TO DO data download


# Can you show me a recent video from the shore camera?
# TO DO data download
