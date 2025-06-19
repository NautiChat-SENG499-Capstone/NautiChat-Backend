toolDescriptions = [
    {
        "type": "function",
        "function": {
            "name": "vectorDB",
            "description": "Retrieves relevant documents from the vector database based on the user prompt including: sensor data, metadata, and more. Should call this function first to get relevant information from the database before calling other functions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "The user's query to retrieve relevant documents.",
                    }
                },
                "required": ["user_prompt"],
            },
        },
    },
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
            "name": "generate_download_codes",
            "description": "Returns a parameters object that includes the deviceCategory and locationCode so that the proper data can be downloaded. The parameters object is defined as follows: params = {\"locationCode\": {locationCode},\"deviceCategoryCode\": {deviceCategory},\"dataProductCode\": \"TSSP\",\"extension\": \"csv\",\"dateFrom\": {todayDate},\"dateTo\": {todayDate},\"dpo_qualityControl\": \"1\",\"dpo_resample\": \"none\",}",
            "parameters": {
                "properties": {
                    "deviceCategory": {
                        "type": "string",
                        "description": "The device category code for which scalar data is requested.",
                    },
                    "locationCode": {
                        "type": "string",
                        "description": "The location code for which the data is requested.",
                    },
                },
                "required": ["deviceCategory", "locationCode"],
                "type": "object",
            },
        },
    },
]
