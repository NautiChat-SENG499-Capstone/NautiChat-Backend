tools = [
    {
        "type": "function",
        "function": {
            "name": "process_scalar_data",
            "description": "Processes sensor data from /scalardata API endpoint. \nArgs: \n json_response: response from API call from /scalardata endpoint. \nReturns: \n JSON object:  json_response from /scalardata endpoint with average, maximum, minimum sensor values & sampling frequencies. The fields 'qaqcFlags', 'sampleTimes', and 'values' are removed.",
            "parameters": {
                "properties": {
                    "json_response": {
                        "type": "object",
                        "description": 'The JSON/dict response directly from the /scalardata endpoint. Expected to contain a "sensorData" key.',
                    }
                },
                "required": ["json_response"],
                "type": "object",
            },
        },
    }
]
