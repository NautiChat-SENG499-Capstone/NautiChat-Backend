import pandas as pd
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
async def get_daily_air_temperature_stats_cambridge_bay(day_str: str) -> str:
    """
    Get daily air temperature statistics for Cambridge Bay.
    Args:
        day_str (str): Date in YYYY-MM-DD format
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
    date_from_str = day_str
    date_to_str = (
        datetime.strptime(day_str, "%Y-%m-%d")
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    params = {
        "locationCode":       "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "propertyCode":       "airtemperature",
        "dateFrom":           date_from_str,
        "dateTo":             date_to_str,
        "rowLimit":           1500,
        "fillGaps":           True,
        "qualityControl":     "clean",
        "token":              ONC_TOKEN,
    }

    raw = onc.getScalardata(params)
    sd = raw.get("sensorData", [])
    if not sd:
        raise RuntimeError(f"No sensorData returned for {day_str!r}")
    block = sd[0]

    # Try both places
    values = block.get("values") or block.get("data", {}).get("values")
    if values is None:
        raise KeyError(f"Couldn't find 'values' in sensorData block; keys were: {list(block)}")

    # Compute stats
    stats = {
        "date":     date_from_str,
        "min":      round(min(values), 2),
        "max":      round(max(values), 2),
        "average":  round(statistics.mean(values), 2),
        "samples":  len(values),
    }
    return stats


# Can you give me an example of 24 hours of oxygen data?
async def get_oxygen_data_24h(day_str: str) -> pd.DataFrame:
    """
    Get 24 hours of dissolved oxygen data for Cambridge Bay.
    Args:
        day_str (str): Date in YYYY-MM-DD format
    Returns:
        pandas DataFrame with datetime + oxygen_ml_per_l columns,
        sampled at 10 minute intervals.
    """
    # Build 24-hour window
    date_from_str = day_str
    date_to_str = (
        datetime.strptime(day_str, "%Y-%m-%d")
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    params = {
        "locationCode":         "CBYIP",
        "deviceCategoryCode":   "OXYSENSOR",
        "propertyCode":         "oxygen",
        "dateFrom":             date_from_str,
        "dateTo":               date_to_str,
        "rowLimit":             1500,
        "fillGaps":             True,
        "qualityControl":       "clean",
        "resamplePeriod":       600,        # In seconds, change for different interval
        "token":                ONC_TOKEN
    }

    # Fetch raw JSON
    raw = onc.getScalardata(params)

    # Pick the first sensor (usually the “corrected” series)
    sensor = raw["sensorData"][0]["data"]
    times = pd.to_datetime(sensor["sampleTimes"])
    values = sensor["values"]

    # Build DataFrame
    df = pd.DataFrame({
        "datetime": times,
        "oxygen_ml_per_l": values
    })
    
    return df.to_string(index=False)


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
async def get_wind_speed_at_timestamp(timestamp_str: str) -> float:
    """
    Get wind speed at Cambridge Bay (in m/s) at the specified timestamp.
    Args:
        timestamp_str (str): ISO‐format timestamp, e.g. '2024-06-23T14:30:00Z'
    Returns:
        float: windspeed at that time (in m/s), or the nearest sample.
    """
    # Parse into datetime and get the date
    dt = pd.to_datetime(timestamp_str)
    date_from_str = dt.strftime("%Y-%m-%d")
    date_to_str = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

    # Fetch relevant data through API request
    params = {
        "locationCode":       "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "propertyCode":       "windspeed",
        "dateFrom":           date_from_str,
        "dateTo":             date_to_str,
        "rowLimit":           1500,
        "fillGaps":           True,
        "qualityControl":     "clean",
        "resamplePeriod":     60,           # In seconds, change for different interval
        "token":              ONC_TOKEN
    }
    raw = onc.getScalardata(params)

    # Extract data block
    block = raw["sensorData"][0]["data"]
    df = pd.DataFrame({
        "timestamp":     pd.to_datetime(block["maxTimes"]),
        "windspeed_m_s": block["max"],
    }).set_index("timestamp")

    # Return exact or nearest
    if dt in df.index:
        return float(df.loc[dt, "windspeed_m_s"])
    
    # Else find nearest index
    idx = df.index.get_indexer([dt], method="nearest")[0]
    return float(df.iloc[idx]["windspeed_m_s"])
    

# I’m doing a school project on Arctic fish. Does the platform have any underwater
# imagery and could I see an example?
# TO DO data download


# How thick was the ice in February this year?
async def get_ice_thickness(start_date: str, end_date: str) -> float:
    """
    Get sea-ice thickness for a range of time in Cambridge Bay.
    Args:
        day_str (str): Date in YYYY-MM-DD format
    Returns:
        JSON string of the scalar data response
    """
    # Include the full end_date by adding one day (API dateTo is exclusive)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    end_date_str = end_dt.strftime("%Y-%m-%d")

    # Fetch relevant data through API request
    params = {
        "locationCode": "CBYSP",
        "deviceCategoryCode": "ICE_BUOY",
        "propertyCode": "icethickness",
        "dateFrom": {start_date},
        "dateTo": {end_date_str},
        "rowLimit": 200,
        "token": {ONC_TOKEN}
    }

    # Fetch all records in the range
    response = onc.getScalardata(params)
    records = response.get("data", [])
    if not records:
        return float("nan")

    # Build DataFrame and group by calendar date
    df = pd.DataFrame(records)
    df["ts"] = pd.to_datetime(df["ts"])
    df["date"] = df["ts"].dt.date
    daily_means = df.groupby("date")["value"].mean()

    # Return the average of those daily means
    return daily_means.mean()


# I would like a plot which shows the water depth so I can get an idea of tides in the Arctic for July 2023
# TO DO data download


# Can you show me a recent video from the shore camera?
# TO DO data download
