tools = [
    {
        "type": "function",
        "function": {
            "name": "process_scalar_data",
            "description": "Processes sensor data from /scalardata API endpoint. This function extracts sensor data, calculates statistical summaries (average, max, min) and determines the sampling frequency.",
            "parameters": {
                "properties": {
                    "json_response": {
                        "type": "object",
                        "description": "The JSON/dict response directly from the /scalardata endpoint. Expected to contain a \"sensorData\" key."
                    } 
                },
                "required": ["json_response"],
                "type": "object",
            },
        }
    }
]