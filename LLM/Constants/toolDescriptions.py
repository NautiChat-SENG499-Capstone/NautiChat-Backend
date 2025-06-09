tools = [
    {
        "type": "function",
        "function": {
            "name": "get_scalar_data_by_device",
            "description": "Gets all the scalar data for the devices at Cambridge Bay based on the deviceInfo provided. The deviceInfo should be a list of dictionaries with deviceCode and dataRating. This list can be obtained from the get_devices_info function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "deviceInfo": {
                        "type": "array",
                        "description": "A list of dictionaries containing deviceCode and dataRating.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "deviceCode": {
                                    "type": "string",
                                    "description": "The unique code of the device."
                                },
                                "dataRating": {
                                    "type": "array",
                                    "description": "A list of data rating objects, each containing dateFrom and dateTo.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "dateFrom": {
                                                "type": "string",
                                                "format": "date-time",
                                                "description": "The start date of the data rating period."
                                            },
                                            "dateTo": {
                                                "type": "string",
                                                "format": "date-time",
                                                "description": "The end date of the data rating period."
                                            }
                                        },
                                        "required": ["dateFrom", "dateTo"]
                                    }
                                }
                            },
                            "required": ["deviceCode", "dataRating"]
                        }
                    }
                },
                "required": ["deviceInfo"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_devices_info",
            "description": "Gets all the devices at Cambridge Bay which returns a list of dictionaries containing the deviceCode and dataRating. dataRating contains dateFrom and dateTo",
            "parameters": {
                "type": "object",
                "properties": {
                    "hasIfsEqual": {
                        "type": "boolean",
                        "description": "set as True if wanting to do a check to see if a a certain device property is equal to a certain value",
                    },
                    "ifEqualKey": {
                        "type": "boolean",
                        "description": "if set hasIfsEqual to True, then this is the key of the device property to check for equality (example: deviceName, deviceCategoryCode, deviceCode, deviceId, hasDeviceData)",
                    },
                    "ifEqualKeyValue": {
                        "type": "string",
                        "description": "if set hasIfsEqual to True, then this is the value of the device property to check for equality",
                    },
                    "hasIfsIn": {
                        "type": "boolean",
                        "description": "set as True if wanting to do a check to see if a certain value is in a device property",
                    },
                    "ifInKey": {
                        "type": "string",
                        "description": "if set hasIfsIn to True, then this is the key of the device property to check for inclusion. (example: deviceName (good for seeing if a device exists with a given name. ex)Oxygen), deviceCategoryCode, deviceCode, deviceId)",
                    },
                    "ifInKeyValue": {
                        "type": "string",
                        "description": "if set hasIfsIn to True, then this is the value to check for inclusion in the device property",
                    },
                    
                },
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_properties_at_cambridge_bay",
    #         "description": "Get a list of properties of data available at Cambridge Bay. The function returns a list of dictionaries. Each Item in the list includes:\n        - description (str): Description of the property. The description may have a colon in it.\n        - propertyCode (str): Property Code of the property\n",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {},
    #         },
    #     },
    # },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_daily_sea_temperature_stats_cambridge_bay",
    #         "description": "Get daily sea temperature statistics for Cambridge Bay\nArgs:\n    day_str (str): Date in YYYY-MM-DD format",
    #         "parameters": {
    #             "properties": {
    #                 "day_str": {
    #                     "type": "string",
    #                     "description": "Date in YYYY-MM-DD format for when daily sea temperature is wanted for",
    #                 }
    #             },
    #             "required": ["day_str"],
    #             "type": "object",
    #         },
    #     },
    # },
]