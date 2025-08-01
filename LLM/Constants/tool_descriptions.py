toolDescriptions = [
    {
        "type": "function",
        "function": {
            "name": "get_active_instruments_at_cambridge_bay",
            "description": (
                "Get the number of currently deployed instruments at Cambridge Bay collecting data, filtered by a"
                " curated list of device category codes. Skips any failed queries silently.\n Returns:\n JSON string:"
                ' Dictionary with instrument count and metadata.\n {\n "activeInstrumentCount": int,\n "details": [ ... ]\n }\n'
                " Note: This function does not take any parameters."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_range_of_available_data",
            "description": (
                "Returns a sorted list of deployment time ranges for instruments at Cambridge Bay for a given device category."
                " Deployment times do not necessarily relate to availability of data, make sure this is clear in the response.\n"
                " Each time range includes:\n - begin (str): ISO 8601 deployment start time\n - end (str | null): ISO 8601 deployment"
                " end time (null if ongoing)\n This function helps identify periods when specific device types were deployed. The data"
                " returned by this function represents the deployments accessed through the ONC API."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "deviceCategoryCode": {
                        "type": "string",
                        "description": "The device category code to filter deployments by (e.g., 'CTD', 'OXYSENSOR').",
                    }
                },
                "required": ["deviceCategoryCode"],
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
                    },
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
            "description": (
                "Get the devices at cambridge bay deployed over the specified time interval including sublocations \nReturns:"
                " \nJSON string: List of deployed devices and their metadata Each item includes: \n- begin (str): deployment"
                " start time \n- end (str): deployment end time \n- deviceCode (str) \n- deviceCategoryCode (str) \n- locationCode (str)"
                " \n- citation (dict): citation metadata (includes description, doi, etc) \nArgs: \ndateFrom (str): ISO 8601 start date"
                " (ex: '2016-06-01T00:00:00.000Z') \ndateTo (str): ISO 8601 end date (ex: '2016-09-30T23:59:59.999Z')"
            ),
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
            "name": "generate_download_codes",
            "description": (
                "Call this function ONLY when the user has explicitly requested to download or retrieve data from Ocean Networks Canada (ONC)."
                " Pass only the parameters that the user has explicitly provided. Do NOT guess, assume, or add any missing parameters. If the user"
                " has not provided dateFrom or dateTo, do NOT include them. The function will handle missing parameters appropriately. After calling"
                " this function, you are NOT responsible for generating any response related to the download result — your task ends here. You should"
                " only call this function when you are certain the user wants data downloaded. Otherwise, do NOT call it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "deviceCategoryCode": {
                        "type": "string",
                        "enum": [
                            "DIVE_COMPUTER",
                            "ROV_CAMERA",
                            "NAV",
                            "ADCP1200KHZ",
                            "ACOUSTICRECEIVER",
                            "CAMLIGHTS",
                            "CTD",
                            "FLNTU",
                            "FLUOROMETER",
                            "HYDROPHONE",
                            "ICEPROFILER",
                            "NITRATESENSOR",
                            "OXYSENSOR",
                            "PHSENSOR",
                            "PLANKTONSAMPLER",
                            "RADIOMETER",
                            "TURBIDITYMETER",
                            "VIDEOCAM",
                            "WETLABS_WQM",
                            "INTERNAL_DEVICE_MONITOR",
                            "ORIENTATION",
                            "ICE_BUOY",
                            "AISRECEIVER",
                            "BARPRESS",
                            "POWER_SUPPLY",
                        ],
                        "description": "The ONC-defined deviceCategoryCode representing the type of device.",
                    },
                    "locationCode": {
                        "type": "string",
                        "enum": ["CBYDS", "CBYIP", "CBYIU", "CBYSP", "CBYSS", "CBYSU"],
                        "description": "The ONC-defined locationCode where the device is deployed. This should be found by either user input or by using the locationCode associated with the deviceCategoryCode. (e.g., 'CBYDS' for the Cambridge Bay Diver data, 'CBYIP' for the Cambridge Bay Underwater Network, 'CBYIU' for the Cambridge Bay Signal Combiner Unit, 'CBYSP' for the Cambridge Bay Safe Passage Buoy, 'CBYSS' for the Cambridge Bay Shore Station, or 'CBYSU' for the Cambridge Bay Signal Combiner Unit).",  # (e.g., 'CBYDS' for the Cambridge Bay Diver data, 'CBYIP' for the Cambridge Bay Underwater Network, 'CBYIU' for the Cambridge Bay Signal Combiner Unit, 'CBYSP' for the Cambridge Bay Safe Passage Buoy, 'CBYSS' for the Cambridge Bay Shore Station, or 'CBYSU' for the Cambridge Bay Signal Combiner Unit).
                    },
                    # "dataProductCode": {
                    #     "type": "string",
                    #     "enum": [
                    #         "LF",
                    #         "MSQAQCR",
                    #         "MP4V",
                    #         "TSSD",
                    #         "TSSP",
                    #         "TSSCP",
                    #         "TSSPPGD",
                    #         "ND",
                    #         "VRF",
                    #         "RADCPTS",
                    #         "RDCUP",
                    #         "RDIP",
                    #         "AF",
                    #         "AD",
                    #         "ASFV",
                    #         "SBCTDRF",
                    #         "CSPPD",
                    #         "HSD",
                    #         "HSPD",
                    #         "SHV",
                    #         "SISUSTS",
                    #         "SRSLMF",
                    #         "JPGF",
                    #         "VQAQCR",
                    #         "VQAQCTSB",
                    #         "VQAQCTSF",
                    #         "VQAQCTSSD",
                    #         "IBPP",
                    #         "IBTSPP",
                    #     ],
                    #     "description": "The ONC-defined dataProductCode for the data product requested. This should be directly related to the extension chosen by the user.",  # (e.g., 'LF' for Log File or 'TSSD' for Time Series Scalar Data)
                    # },
                    "extension": {
                        "type": "string",
                        "enum": [
                            "txt",
                            "asf",
                            "qaqc",
                            "json",
                            "mat",
                            "png",
                            "zip",
                            "mp4",
                            "vrl",
                            "nc",
                            "fft",
                            "flac",
                            "raw",
                            "wav",
                            "an",
                            "csv",
                            "pdf",
                            "jpg",
                        ],
                        "description": "The extension in which the download should be downloaded as.",
                    },
                    "dateFrom": {
                        "type": "string",
                        "description": "The start date for the data request, in ISO 8601 format (e.g., 'YYYY-MM-DDTHH:MM:SS.sssZ').",
                    },
                    "dateTo": {
                        "type": "string",
                        "description": "The end date for the data request, in ISO 8601 format (e.g., 'YYYY-MM-DDTHH:MM:SS.sssZ').",
                    },
                    "dpo_qualityControl": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "Whether to apply quality control to the data. If 1, the function will apply quality control; if 0, it will not.",
                    },
                    "dpo_dataGaps": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "Whether to include data gaps in the response. If 1, the function will include data gaps; if 0, it will not and instead fill missing/bad data with NaNs (Not a number).",
                    },
                    "dpo_resample": {
                        "type": "string",
                        "enum": ["none", "average", "minMax", "minMaxAvg"],
                        "description": "The resampling type to apply to the data. Must be one of: 'none', 'average', 'minMax', or 'minMaxAvg'. Use 'average' to return average values per interval, 'minMax' for only minimum and maximum values, and 'minMaxAvg' for all three. Set to 'none' if no resampling is needed. Choose based on how the user describes the summary they want (e.g., average, min/max, or all three (min, max, and average)).",
                    },
                    "dpo_minMax": {
                        "type": "integer",
                        "enum": [60, 300, 900, 3600, 86400],
                        "description": "The specified resample interval seconds for the minimum and maximum resampling. Allowed values: 60=1Minute, 300=5Minutes, 900=15Minutes, 3600=1Hour, 86400=1Day.",
                    },
                    "dpo_average": {
                        "type": "integer",
                        "enum": [60, 300, 900, 3600, 86400],
                        "description": "The specified resample interval seconds for the average resampling. Allowed values: 60=1Minute, 300=5Minutes, 900=15Minutes, 3600=1Hour, 86400=1Day.",
                    },
                    "dpo_minMaxAvg": {
                        "type": "integer",
                        "enum": [60, 300, 900, 3600, 86400],
                        "description": "The specified resample interval in seconds for the minimum, maximum, and average. Allowed values: 60=1Minute, 300=5Minutes, 900=15Minutes, 3600=1Hour, 86400=1Day.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_air_temperature_stats_cambridge_bay",
            "description": (
                "Get daily air temperature statistics (date, min, max, average, sample count) for Cambridge Bay on a given date."
                " Temperature should be expressed in degrees Celsius. If no data exists for that time range then tell the user that"
                " no data exists for that time range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": 'Date in YYYY-MM-DD format, (e.g. "2024-06-23").',
                    },
                },
                "required": ["date_from_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_oxygen_data_24h",
            "description": (
                "Retrieve 24 hours of Oxygen data (dissolved oxygen measurements) (in mL/L) for Cambridge Bay at 1-hour intervals."
                " The function returns the oxygen levels with their corresponding dates.  If no date is provided a default date of"
                " '2024-06-24' is used, which is guaranteed to have data. If no data exists for that time range then tell the user"
                " that no data exists for that time range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": 'Date in YYYY-MM-DD format, (e.g. "2024-06-24").',
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ship_noise_acoustic_for_date",
            "description": (
                "Submit a request to retrieve 24 hours of ship noise acoustic data (WAV format) "
                "from the Cambridge Bay hydrophone using Ocean Networks Canada's dataProductDelivery API. "
                "This function initiates a request for the 'AD' (acoustic data) product and returns metadata "
                "about the order, including the request ID, request parameters, and a status code. "
                "Note: It does not download or return the audio file itself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format representing the start of the 24-hour window.",
                    },
                },
                "required": ["date_from_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_spectrogram_for_date",
            "description": (
                "Submit a request for a 24-hour ship noise spectrogram (PNG image) from the Cambridge Bay hydrophone "
                "using Ocean Networks Canada's dataProductDelivery API. The function requests the 'HSD' data product, "
                "returning a request ID, order metadata, the parameters used, and a status code. "
                "It does not return the spectrogram image itself, but allows for tracking or downloading it later."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format representing the start of the 24-hour window.",
                    },
                },
                "required": ["date_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wind_speed_at_timestamp",
            "description": (
                "Get wind speed (m/s) at Cambridge Bay for a given day and Hour of that day, returning the exact or nearest sample."
                " Wind speed is expressed in meters per second (m/s). If no data exists for that time range then tell the user that"
                " no data exists for that time range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": 'Date to get wind speed in YYYY-MM-DD format, (e.g. "2024-06-24").',
                    },
                    "hourInterval": {
                        "type": "integer",
                        "description": "Hour of the day wanted for windspeed, default is 12 (noon)",
                    },
                },
                "required": ["date_from_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ice_thickness",
            "description": (
                "Get the average daily sea-ice thickness the days provided (inclusive) for Cambridge Bay."
                " Returns the average ice thickness representing the mean ice thickness (in meters) for the"
                " days given (inclusive), or -1 if no data is found. If you get the -1 value returned tell the"
                " user that no data exists for that time range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from_str": {
                        "type": "string",
                        "description": 'Start date in YYYY-MM-DD format (e.g. "2024-02-01").',
                    },
                    "date_to_str": {
                        "type": "string",
                        "description": 'End date in YYYY-MM-DD format (e.g. "2024-02-01").',
                    },
                },
                "required": ["date_from_str", "date_to_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scalar_data",
            "description": "Call this function ONLY when the user has explicitly requested for scalar data. Pass only the parameters that the user has explicitly provided. Do NOT guess, assume, or add any missing parameters. If the user has not provided dateFrom or dateTo, do NOT include them. The function will handle missing parameters appropriately. You should only call this function when you are certain the user wants scalar data. Otherwise, do NOT call it.",  # Get the deviceCategoryCode at a certain locationCode at Cambridge Bay in a propertyCode with a resamplePeriod and resampleType, so that users can request scalar data over a specified time period. Returns the result of a scalar data request. This function performs a data request to the ONC API, then returns the data to the LLM. If this function is called, the LLM will only provide the parameters the user has explicitly given. DO NOT guess, assume, or invent any parameters. DO NOT add any parameters unless they're explicitly given. If parameters are missing, the function will handle asking the user for them. If that device isn't deployed at that time, the LLM will respond with the deployment times. If there is no data from the device during a deployed time, the LLM will tell the user and not invent data. Returns: result (str): The result of the data request. Args: deviceCategoryCode (str): An ONC-defined code identifying the type of device; locationCode (str): An ONC-defined code identifying the location of the device; propertyCode (str): An ONC-defined code identifying the type of data being requested; dateFrom (str): The start date of the data request in ISO 8601 format; dateTo (str): The end date of the data request in ISO 8601 format.
            "parameters": {
                "type": "object",
                "properties": {
                    "deviceCategoryCode": {
                        "type": "string",
                        "enum": [
                            "",
                            "DIVE_COMPUTER",
                            "ROV_CAMERA",
                            "NAV",
                            "ADCP1200KHZ",
                            "ACOUSTICRECEIVER",
                            "CAMLIGHTS",
                            "CTD",
                            "FLNTU",
                            "FLUOROMETER",
                            "HYDROPHONE",
                            "ICEPROFILER",
                            "NITRATESENSOR",
                            "OXYSENSOR",
                            "PHSENSOR",
                            "PLANKTONSAMPLER",
                            "RADIOMETER",
                            "TURBIDITYMETER",
                            "VIDEOCAM",
                            "WETLABS_WQM",
                            "INTERNAL_DEVICE_MONITOR",
                            "ORIENTATION",
                            "ICE_BUOY",
                            "AISRECEIVER",
                            "BARPRESS",
                            "POWER_SUPPLY",
                            "CO2SENSOR",
                            "JB",
                            "ADAPTER",
                            "METSTN",
                        ],
                        "description": "The ONC-defined deviceCategoryCode representing the type of device.",
                    },
                    "locationCode": {
                        "type": "string",
                        "enum": [
                            "",
                            "CBY",
                            "CBYDS",
                            "CBYIJ.J1",
                            "CBYIJ.J2",
                            "CBYIP",
                            "CBYIP.D1",
                            "CBYIP.D2",
                            "CBYIP.D3",
                            "CBYIP.D4",
                            "CBYIP.K1",
                            "CBYIP.K2",
                            "CBYIP.K3",
                            "CBYIU",
                            "CBYIU.AC1",
                            "CBYIU.AC2",
                            "CBYIU.AC3",
                            "CBYIU.AC4",
                            "CBYIU.AC5",
                            "CBYSP",
                            "CBYSS",
                            "CBYSS.M1",
                            "CBYSS.M2",
                            "CBYSU",
                            "CBYSU.AC1",
                            "CBYSU.AC2",
                            "CF240",
                        ],
                        "description": "The ONC-defined locationCode where the device is deployed.",
                    },
                    "propertyCode": {
                        "type": "string",
                        "enum": [
                            "",
                            "depth",
                            "latitude",
                            "longitude",
                            "seawatertemperature",
                            "amperage",
                            "voltage",
                            "temperature",
                            "oxygen",
                            "conductivity",
                            "salinity",
                            "density",
                            "nitrate",
                            "chlorophyll",
                            "turbidity",
                            "fluorescence",
                            "backscatter",
                            "radiance",
                            "irradiance",
                            "ph",
                            "co2",
                            "orientation",
                            "pressure",
                            "electricalresistance",
                            "groundfault",
                            "internaltemperature",
                            "statuscode",
                            "icedraft",
                            "pingtime",
                            "soundpressurelevel",
                            "targetpersistence",
                            "tilt",
                            "totalpressure",
                            "cameralight",
                            "camerapan",
                            "cameratilt",
                            "focus",
                            "zoom",
                            "parphotonbased",
                            "batterycharge",
                            "internalhumidity",
                            "nitrateconcentration",
                            "internalph",
                            "magneticheading",
                            "pitch",
                            "roll",
                            "soundspeed",
                            "sigmat",
                            "sigmatheta",
                            "chlorophyll",
                            "turbidityntu",
                            "gassaturation",
                            "resevoirvolume",
                            "co2concentrationlinearized",
                            "co2partialpressure",
                            "gasstreampressure",
                            "scientificcount",
                            "calibratedphaseangle",
                            "compensatedphaseangle",
                            "biofoulingprevention",
                            "dewpoint",
                            "onoffsensor",
                            "absolutebarometricpressure",
                            "airtemperature",
                            "barometrictrend",
                            "rainfallrate",
                            "relativebarometricpressure",
                            "relativehumidity",
                            "solarradiation",
                            "uvindex",
                            "airdensity",
                            "absolutehumidity",
                            "mixingratio",
                            "specificenthalpy",
                            "wetbulbtemperature",
                            "windchilltemperature",
                            "winddirection",
                            "windspeed",
                            "benderelectricalresistance",
                            "cdom",
                        ],
                        "description": "The ONC-defined propertyCode for the scalar data requested (Should not be assumed)",  # (e.g., 'depth' for depth etc.)
                    },
                    "dateFrom": {
                        "type": "string",
                        "description": "The start date for the data request, in ISO 8601 format.",
                    },
                    "dateTo": {
                        "type": "string",
                        "description": "The end date for the data request, in ISO 8601 format.",
                    },
                },
                "required": [],
            },
        },
    },
]
