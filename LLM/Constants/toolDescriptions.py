toolDescriptions = [
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "vectorDB",
    #         "description": "Retrieves relevant documents from the vector database based on the user prompt including: sensor data, metadata, and more. Should call this function first to get relevant information from the database before calling other functions.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "user_prompt": {
    #                     "type": "string",
    #                     "description": "The user's query to retrieve relevant documents.",
    #                 }
    #             },
    #             "required": ["user_prompt"],
    #         },
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "get_properties_at_cambridge_bay",
            "description": "Get a list of properties available at Cambridge Bay. The function returns a list of dictionaries. Each Item in the list includes:\n        - description (str): Description of the property. The description may have a colon in it.\n        - propertyCode (str): Property Code of the property\n",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_instruments_at_cambridge_bay",
            "description": (
                "Get the number of currently deployed instruments at Cambridge Bay collecting data, filtered by a curated list of device category codes. Skips any failed queries silently.\n Returns:\n JSON string: Dictionary with instrument count and metadata.\n {\n \"activeInstrumentCount\": int,\n \"details\": [ ... ]\n }\n Note: This function does not take any parameters"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_time_range_of_available_data",
    #         "description": (
    #             "Returns a sorted list of deployment time ranges for instruments at Cambridge Bay for a given device category.\n Each time range includes:\n - begin (str): ISO 8601 deployment start time\n - end (str | null): ISO 8601 deployment end time (null if ongoing)\n This function helps identify periods when specific device types were deployed."
    #         ),
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "deviceCategoryCode": {
    #                     "type": "string",
    #                     "description": "The device category code to filter deployments by (e.g., 'CTD', 'OXYSENSOR')."
    #                 }
    #             },
    #             "required": ["deviceCategoryCode"]
    #         }
    #     }
    # },
    {
        "type": "function",
        "function": {
            "name": "get_daily_sea_temperature_stats_cambridge_bay",
            "description": "Get daily sea temperature statistics for Cambridge Bay\nArgs:\n    day_str (str): Date in YYYY-MM-DD format",
            "parameters": {
                "properties": {
                    "day_str": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format for when daily sea temperature is wanted for",
                    }
                },
                "required": ["day_str"],
                "type": "object",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_deployed_devices_over_time_interval",
            "description": "Get the devices at cambridge bay deployed over the specified time interval including sublocations \nReturns: \nJSON string: List of deployed devices and their metadata Each item includes: \n- begin (str): deployment start time \n- end (str): deployment end time \n- deviceCode (str) \n- deviceCategoryCode (str) \n- locationCode (str) \n- citation (dict): citation metadata (includes description, doi, etc) \nArgs: \ndateFrom (str): ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z') \ndateTo (str): ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')",
            "parameters": {
                "properties": {
                    "dateFrom": {
                        "type": "string",
                        "description": "ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')",
                    },
                    "dateTo": {
                        "type": "string",
                        "description": "ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')",
                    },
                },
                "required": ["dateFrom", "dateTo"],
                "type": "object",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scalar_data_by_device",
            "description": "gets the scalar data for a device at cambridge bay over a specified time interval, given the device code and time range",
            "parameters": {
                "properties": {
                    "deviceCode": {
                        "type": "string",
                        "description": "The device code for which scalar data is requested.",
                    },
                    "dateFrom": {
                        "type": "string",
                        "description": "ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')",
                    },
                    "dateTo": {
                        "type": "string",
                        "description": "ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')",
                    },
                },
                "required": ["deviceCode", "dateFrom", "dateTo"],
                "type": "object",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_air_temperature_stats_cambridge_bay",
            "description": "Get daily air temperature statistics (date, min, max, average, sample count) for Cambridge Bay on a given date. Temperature should be expressed in degrees Celsius. If no data exists for that time range then tell the user that no data exists for that time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format, (e.g. \"2024-06-23\")."
                    },
                },
                "required": ["date_from_str"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_oxygen_data_24h",
            "description": "Retrieve 24 hours of Oxygen data (dissolved oxygen measurements) (in mL/L) for Cambridge Bay at 1-hour intervals. The function returns the oxygen levels with their corresponding dates.  If no date is provided a default date of '2024-06-24' is used, which is guaranteed to have data. If no data exists for that time range then tell the user that no data exists for that time range. ",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format, (e.g. \"2024-06-24\")."
                    },
                },
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ship_noise_for_date",
            "description": "Get 24 hours of ship-noise data for Cambridge Bay on a specific date, returned as a JSON string of the full time series.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (e.g. \"2024-07-31\") for which to retrieve ship-noise data."
                    },
                },
                "required": ["date_from_str"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wind_speed_at_timestamp",
            "description": "Get wind speed (m/s) at Cambridge Bay for a given day and Hour of that day, returning the exact or nearest sample. Wind speed is expressed in meters per second (m/s). If no data exists for that time range then tell the user that no data exists for that time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": "Date to get wind speed in YYYY-MM-DD format, (e.g. \"2024-06-24\")."
                    },
                    "hourInterval": {
                        "type": "integer",
                        "description": "Hour of the day wanted for windspeed, default is 12 (noon)"
                    },
                },
                "required": ["date_from_str"]
            },
        },  
    },
    {
        "type": "function",
        "function": {
            "name": "get_ice_thickness",
            "description": "Get the average daily sea-ice thickness the days provided (inclusive) for Cambridge Bay. Returns the average ice thickness representing the mean ice thickness (in meters) for the days given (inclusive), or -1 if no data is found. If you get the -1 value returned tell the user that no data exists for that time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g. \"2024-02-01\")."
                    },
                    "date_to_str": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g. \"2024-02-01\")."
                    },
                },
                "required": ["date_from_str", "date_to_str"]
            },
        },
    },
]
