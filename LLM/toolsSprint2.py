from datetime import datetime, timedelta


async def get_daily_air_temperature_stats_cambridge_bay(day_str: str):
    """
    Get daily air temperature statistics for Cambridge Bay
    Args:
        day_str (str): Date in YYYY-MM-DD format
    """
    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = datetime.strptime(day_str, "%Y-%m-%d") + timedelta(days=1)
    date_to_str = date_to.strftime("%Y-%m-%d")  # Convert back to string

    async with httpx.AsyncClient() as client:
        # Get data from ONC API
        temp_api = (
            f"https://data.oceannetworks.ca/api/scalardata/location?"
            f"locationCode={CAMBRIDGE_LOCATION_CODE}&"
            f"deviceCategoryCode=METEO&"
            f"propertyCode=airt&"
            f"dateFrom={day_str}&"
            f"dateTo={date_to_str}&"
            f"rowLimit=80000&"
            f"outputFormat=Object&"
            f"resamplePeriod=86400&"
            f"token={ONC_TOKEN}"
        )
        response = await client.get(temp_api)
        response.raise_for_status()
        response = response.json()

    if response["sensorData"] is None:
        return json.dumps({"result": "No air temperature data available for the given date."})

    data = response["sensorData"][0]["data"][0]

    # Get min, max, and average and store in dictionary
    return json.dumps(
        {
            "daily_min": round(data["minimum"], 2),
            "daily_max": round(data["maximum"], 2),
            "daily_avg": round(data["value"], 2),
        }
    )
