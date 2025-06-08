import datetime
from datetime import datetime, timedelta



def process_scalar_data(json_response):
    """Processes sensor data from /scalardata API endpoint.

    This function extracts sensor data, calculates statistical summaries
    (average, max, min) and determines the sampling frequency. It then
    modifies the input JSON response to include these summaries while
    removing the raw data arrays.

    Args:
        json_response (dict): The JSON response directly from the /scalardata endpoint.
                              Expected to contain a "sensorData" key.
                              Each entry should have "data" field with "values",
                              "qaqcFlags", and "sampleTimes".

    Returns:
        dict: The modified JSON response with raw data replaced by
              calculated statistics (averageSensorValue, maxSensorValue,
              minSensorValue, sampleFrequency) and outputFormat set to "Number".
    """

    # Check if sensorData exists
    if json_response["sensorData"] is None:
        print("No field sensorData from /scalardata endpoint to process")
        return json_response
    
    sensor_data_content = json_response["sensorData"]

    average_sensor_value = 0
    max_sensor_value = 0
    min_sensor_value = 1000
    sample_frequency = ""

    for entry in sensor_data_content:
        #Sensor data values
        data_sample_values = entry["data"]["values"]

        #Compute average, min, max sensor value
        average_sensor_value = sum(data_sample_values)/entry["actualSamples"]
        max_sensor_value = max(data_sample_values)
        min_sensor_value = min(data_sample_values)

        #Delete values & qaqcFlags list since we're replacing with average values
        del entry["data"]["values"]
        del entry["data"]["qaqcFlags"]

        #Get sampleTimes list
        sample_times = entry["data"]["sampleTimes"]
        
        #We need 2 or more values get sample frequency
        if len(sample_times) < 2:
            print("Need at least two sample times to calculate an average interval.")
        else:
            # Convert all strings to datetime objects
            # Replace 'Z' with '+00:00' for proper ISO 8601 parsing as UTC
            parsed_times = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in sample_times]

            total_duration = timedelta(0)
            for i in range(len(parsed_times) - 1):
                total_duration += (parsed_times[i+1] - parsed_times[i])
            average_interval = total_duration / (len(parsed_times) - 1)
            
            # Format the output for readability
            seconds = average_interval.total_seconds()
            if seconds < 60:
                sample_frequency = f"Every {seconds:.3f} seconds"
            elif seconds < 3600:
                sample_frequency = f"Every {seconds / 60:.2f} minutes"
            elif seconds < 86400:
                sample_frequency = f"Every {seconds / 3600:.2f} hours"
            else:
                sample_frequency = f"Every {seconds / 86400:.2f} days"
            del entry["data"]["sampleTimes"]
        print(f"Sample frequency: {sample_frequency}")
        print(f"average sensor value: {average_sensor_value}")

        #Update new fields to dict after removing the old ones
        entry["data"]["sampleFrequency"] = sample_frequency
        entry["data"]["averageSensorValue"] = average_sensor_value
        entry["data"]["maxSensorValue"] = max_sensor_value
        entry["data"]["minSensorValue"] = min_sensor_value
        entry["outputFormat"] = "Number"
    
    return json_response

