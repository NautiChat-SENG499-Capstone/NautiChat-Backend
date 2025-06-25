import pandas as pd
from onc import ONC
from datetime import datetime, timedelta


onc = ONC("6a316121-e017-4f4c-9cb1-eaf5dd706425")
day_str = "2024-06-24"
date_from_str = day_str
date_to_str = (
    datetime.strptime(day_str, "%Y-%m-%d")
    + timedelta(days=1)
).strftime("%Y-%m-%d")
params = {
    "locationCode": "CBYSS.M2",
    "deviceCategoryCode": "METSTN",
    "dateFrom":           date_from_str,
    "dateTo":             date_to_str,
}

data = onc.getScalardata(params)
sensorData = data.get("sensorData", [])
temps = sensorData[0]["data"]["values"]
mean = sum(temps) / len(temps)
max_temp = max(temps)
min_temp = min(temps)
temps = {
    "mean": mean,
    "max_temp": max_temp,
    "min_temp": min_temp,
    "samples": len(temps),
    "date": date_from_str
}
print(temps)

print()
print()
print()


date_from_str = day_str
date_to_str = (
    datetime.strptime(day_str, "%Y-%m-%d")
    + timedelta(days=1)
).strftime("%Y-%m-%d")

params = {
    "locationCode":         "CBYIP",
    "deviceCategoryCode":   "OXYSENSOR",
    "propertyCode":         "oxygen",
    "dateFrom":             date_from_str,
    "dateTo":               date_to_str,
    #"metadata":           "Full",
    "resamplePeriod":       3600,        # In one hour intervals
}

# Fetch raw JSON
raw = onc.getScalardata(params)
#print(raw)
# Pick the first sensor (usually the “corrected” series)
sensor = raw["sensorData"][0]["data"]
times = sensor["sampleTimes"]
values = sensor["values"]

# Build DataFrame
df ={
    "datetime": times[0:24],
    "oxygen_ml_per_l": values[0:24]
}
print(df)
print()
print()
print()

day_str = "2025-03-01"
date_from_str = day_str
date_to_str = (
    datetime.strptime(day_str, "%Y-%m-%d")
    + timedelta(days=1)
).strftime("%Y-%m-%d")
time_to_find =  (datetime.strptime(day_str, "%Y-%m-%d")
                + timedelta(hours=12, minutes=0, seconds=0)
            )
print(date_from_str, date_to_str, time_to_find)
params = {
        "locationCode":       "CBYSS.M2",
        "deviceCategoryCode": "METSTN",
        "propertyCode":       "windspeed",
        "dateFrom":           date_from_str,
        "dateTo":             date_to_str,     
    }
raw = onc.getScalardata(params)

# Extract data block
block = raw["sensorData"][0]["data"]
#print(block["sampleTimes"])
threshold = timedelta(seconds=30)
matching_indices = [
    i for i, ts in enumerate(block["sampleTimes"])
    if abs(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ") - time_to_find) <= threshold
]
# print(block["sampleTimes"][(matching_indices[0]-10):(matching_indices[0]+10)])
# print(block["values"][(matching_indices[0]-10):(matching_indices[0]+10)])
# print()
wind_speed_at_time = block["values"][matching_indices[0]] if matching_indices else None
data = {
    "datetime": time_to_find.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "wind_speed_m_s": wind_speed_at_time
}
print(data)
print()
print()
print()
day_str = "2025-06-23"
date_from_str = day_str
date_to_str = (
    datetime.strptime(day_str, "%Y-%m-%d")
    + timedelta(days=1)
).strftime("%Y-%m-%d")

params = {
        "locationCode": "CBYIP",
        "deviceCategoryCode": "ICEPROFILER",
        "sensorCategoryCodes": "ice_thickness_corrected",
        "dateFrom": {date_from_str},
        "dateTo": {date_to_str},
    }

# Fetch all records in the range
response = onc.getScalardata(params)
records = response["sensorData"]
# for i, keys in enumerate(records):
#     #print(f"Dict {i} keys:", keys)

all_keys = set()
i = 0
for d in records:
    all_keys.update(d.keys())
    print(i)
    i += 1
    print(d["outputFormat"])
    print(d["sensorCode"])
    print(d["actualSamples"])
    print(d["sensorName"])
    print(d["sensorCategoryCode"])
    print(d["unitOfMeasure"])
    print(d["propertyCode"])
    print(d["data"].keys())
test = records[0]["data"]["values"][0:10]
print(test)
values = records[0]["data"]["values"]
flags = records[0]["data"]["qaqcFlags"]
# All unique keys: {'data', 'sensorCode', 'outputFormat', 'actualSamples', 'sensorName', 'sensorCategoryCode', 'unitOfMeasure', 'propertyCode'}
print("All unique keys:", all_keys)
data = [val for index, val in enumerate(values) if (val is not None and flags[index] <3)]
average_ice_thickness = sum(data) / len(data) if data else None
print("Average ice thickness:", average_ice_thickness)
