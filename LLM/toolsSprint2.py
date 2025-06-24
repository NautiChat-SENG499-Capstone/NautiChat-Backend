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
async def get_daily_air_temperature_stats_cambridge_bay(day_str: str):
    """
    Get daily air temperature statistics for Cambridge Bay.
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
        "locationCode": "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "propertyCode": "airtemperature",
        "dateFrom": {date_from_str},
        "dateTo": {date_to_str},
        "rowLimit": 500,
        "token": {ONC_TOKEN}
    }
    data = onc.getScalardata(params)

    return data


# Can you give me an example of 24 hours of oxygen data?
async def get_oxygen_data_24h(day_str: str):
    """
    Get 24 hours of dissolved oxygen data for Cambridge Bay.
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
        "deviceCategoryCode": "OXYSENSOR",
        "propertyCode": "oxygen",
        "dateFrom": {date_from_str},
        "dateTo": {date_to_str},
        "rowLimit": 250,
        "token": {ONC_TOKEN}
    }
    data = onc.getScalardata(params)

    return data


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
async def get_wind_speed_at_time(day_str: str):
    """
    Get the wind speed at a specific timestamp in Cambridge Bay.
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
        "locationCode": "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "propertyCode": "windspeed",
        "dateFrom": {date_from_str},
        "dateTo": {date_to_str},
        "rowLimit": 200,
        "token": {ONC_TOKEN}
    }
    data = onc.getScalardata(params)

    return data
    

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
