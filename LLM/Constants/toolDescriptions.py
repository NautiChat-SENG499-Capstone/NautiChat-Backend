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
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_deployed_devices_over_time_interval",
    #         "description": "Get the devices at cambridge bay deployed over the specified time interval including sublocationsReturns:\
    #                 JSON string: List of deployed devices and their metadata Each item includes:\
    #                     - begin (str): deployment start time\
    #                     - end (str): deployment end time\
    #                     - deviceCode (str)\
    #                     - deviceCategoryCode (str)\
    #                     - locationCode (str)\
    #                     - citation (dict): citation metadata (includes description, doi, etc)\
    #                 Args:\
    #                     dateFrom (str): ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')\
    #                     dateTo (str): ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')",
    #         "parameters": {
    #             "properties": {
    #                 "dateFrom": {
    #                     "type": "string",
    #                     "description": "ISO 8601 start date (ex: '2016-06-01T00:00:00.000Z')",
    #                 },
    #                 "dateTo": {
    #                     "type": "string",
    #                     "description": "ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')",
    #                 },
    #             },
    #             "required": ["dateFrom", "dateTo"],
    #             "type": "object",
    #         },
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "get_devices_info",
            "description": "Retrieves a list of devices at Cambridge Bay with optional filtering based on equality or substring matching of device attributes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hasIfsEqual": {
                        "type": "boolean",
                        "description": "Set to true to enable equality-based filtering on a specific device attribute."
                    },
                    "ifEqualKey": {
                        "type": "string",
                        "description": "The key of the device attribute to compare for equality. Required if hasIfsEqual is true."
                    },
                    "ifEqualKeyValue": {
                        "type": "string",
                        "description": "The value that the specified attribute must match exactly. Required if hasIfsEqual is true."
                    },
                    "hasIfsIn": {
                        "type": "boolean",
                        "description": "Set to true to enable substring-based filtering on a specific device attribute."
                    },
                    "ifInKey": {
                        "type": "string",
                        "description": "The key of the device attribute to check for substring inclusion. Required if hasIfsIn is true."
                    },
                    "ifInKeyValue": {
                        "type": "string",
                        "description": "The substring that must be present in the specified attribute. Required if hasIfsIn is true."
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_scalar_data_by_device",
            "description": "Retrieves scalar data for a list of devices at Cambridge Bay using the provided device codes and their associated date ranges from data ratings.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }

    
]
