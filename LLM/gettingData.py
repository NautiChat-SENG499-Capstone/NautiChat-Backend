from onc import ONC
import json
import matplotlib.pyplot as plt

onc = ONC("4289f1b9-e1cb-4cf8-b5fb-20d88dcf7eec")


async def get_properties_at_cambridge_bay():
    """Get a list of properties of data available at Cambridge Bay
    Returns a list of dictionaries turned into a string.
    Each Item in the list includes:
    - description (str): Description of the property. The description may have a colon in it.
    - propertyCode (str): Property Code of the property
    example: '{"Description of the property": Property Code of the property}'
    """
    property_API = f"https://data.oceannetworks.ca/api/properties?locationCode={CAMBRIDGE_LOCATION_CODE}&token={ONC_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.get(property_API)
        response.raise_for_status()  # Error handling

        # Convert from JSON to Python dictionary for cleanup, return as JSON string
        raw_data = response.json()
        list_of_dicts = [
            {"description": item["description"], "propertyCode": item["propertyCode"]}
            for item in raw_data
        ]
        return json.dumps(list_of_dicts)

# deviceInfo = []
# params = {
#     "locationCode": "CBYIP",
# }
# devices = onc.getDevices(params)
# for device in devices:
#     if "deviceCode" in device and device["deviceCategoryCode"] == "FLNTU":
#       #print(json.dumps(device, indent=2))
#       deviceInfo.append({"deviceCode": device["deviceCode"], "dataRating": device["dataRating"]})
      #deviceInfo.append(device["deviceCode"])
# dev1Code = devices[0]["deviceCategoryCode"]
# print(dev1Code)
# params = {
#     "deviceCategoryCode": dev1Code,
# }
# dev1 = onc.getDevices(params)
# print(json.dumps(dev1, indent=2))

#print(deviceInfo)
"""
{
  "cvTerm": {
    "device": [
      {
        "uri": "http://vocab.nerc.ac.uk/collection/L22/current/TOOL1250/",
        "vocabulary": "SeaVoX Device Catalogue"
      }
    ]
  },
  "dataRating": [
    {
      "dateFrom": "2014-09-22T18:30:00.000Z",
      "dateTo": null,
      "samplePeriod": 5.0,
      "sampleSize": 1
    }
  ],
  "deviceCategoryCode": "ICEPROFILER",
  "deviceCode": "ASLSWIP53019",
  "deviceId": 23369,
  "deviceLink": "https://data.oceannetworks.ca/DeviceListing?DeviceId=23369",
  "deviceName": "ASL Shallow Water Ice Profiler 53019",
  "hasDeviceData": true
}

"""

def get_devices_info_by_params(onc, params, hasIfsEqual = False, ifEqualKey = None, ifEqualKeyValue = None, hasIfsIn = False, ifInKey = None, ifInKeyValue = None):
    """Get devices based on the provided parameters."""
    deviceInfo = []
    devices = onc.getDevices(params)
    for device in devices:
      if hasIfsEqual:
        if device[ifEqualKey] == ifEqualKeyValue:
          deviceInfo.append({"deviceCode": device["deviceCode"], "dataRating": device["dataRating"]})
      elif hasIfsIn:
        if ifInKeyValue.lower() in device[ifInKey].lower():
          deviceInfo.append({"deviceCode": device["deviceCode"], "dataRating": device["dataRating"]})
      else:
        deviceInfo.append({"deviceCode": device["deviceCode"], "dataRating": device["dataRating"]})
    return deviceInfo

params = {
    "locationCode": "CBYIP",
    #"deviceName": "oxygen",
}
deviceInfo = get_devices_info_by_params(onc, params, hasIfsIn=True, ifInKey="deviceName", ifInKeyValue="OXYGEN")


# params = {
#     "description": "doppler",
# }
# catDesc = onc.getDeviceCategories(params)
# print(json.dumps(catDesc, indent=2))



# params = {
#     "locationCode": "CBYIP",
# }
# devs = onc.getDevices(params)

# print(json.dumps(devs, indent=2))

# params = {
#     "deviceCode": "doppler",
# }
# catDesc = onc.getDeviceCategories(params)
# print(json.dumps(catDesc, indent=2))


# params = {
#     "deviceCategoryCode": "FLNTU",
# }
# catDesc = onc.getDataProducts(params)
# print(json.dumps(catDesc, indent=2))


# params = {
#     "locationCode": "CBYIP",
    
# }
# data = onc.getDataProducts(params)
# print(json.dumps(data, indent=2))


# params = {
    #   #"locationCode": "CBYIP", #Dont need for deviceCode
    #   #"deviceCategoryCode": "FLNTU",
    #   "deviceCode": device,
    #   "dateFrom": "2016-09-01T00:00:00.000Z",
    #   "dateTo": "2016-09-01T00:01:00.000Z",
    # }


def get_scalar_data_by_device(onc, deviceInfo):
  ScalarData=[]
  for device in deviceInfo:
    for samplePeriod in device["dataRating"]:
      params = {
        "deviceCode": device["deviceCode"],
        "dateFrom": samplePeriod["dateFrom"],
        "dateTo": samplePeriod["dateTo"],
      }
      scalarData = onc.getScalardata(params)
      if("sensorData" in scalarData and scalarData["sensorData"] is not None):
      for sensorData in scalarData["sensorData"]:
        filtered_times = [t for l, t in zip(sensorData["data"]["qaqcFlags"], sensorData["data"]["sampleTimes"]) if l == 1]#If l!=1 then it is invalid data or NaN (missing data)
        filtered_values = [t for l, t in zip(sensorData["data"]["qaqcFlags"], sensorData["data"]["values"]) if l == 1]
        if(len(filtered_times)>0): #So not making empty plots
          ScalarData.append({"deviceCode": device["deviceCode"], "data": {"sampleTimes": filtered_times, "values": filtered_values}})

  return ScalarData

allScalarData = get_scalar_data_by_device(onc, deviceInfo)

for device in deviceInfo:
  for samplePeriod in device["dataRating"]:
    params = {
      "deviceCode": device["deviceCode"],
      "dateFrom": samplePeriod["dateFrom"],
      "dateTo": samplePeriod["dateTo"],
  }
    
    scalarData = onc.getScalardata(params)
    keys = scalarData.keys()
    print(keys)
    if("sensorData" in scalarData):
      print("Found sensorData")
    if("sensorData" in scalarData and scalarData["sensorData"] is not None):
      #print(json.dumps(scalarData, indent=2))
      for sensorData in scalarData["sensorData"]:
        filtered_times = [t for l, t in zip(sensorData["data"]["qaqcFlags"], sensorData["data"]["sampleTimes"]) if l == 1]#If l!=1 then it is invalid data or NaN (missing data)
        filtered_values = [t for l, t in zip(sensorData["data"]["qaqcFlags"], sensorData["data"]["values"]) if l == 1]
        if(len(filtered_times)>0): #So not making empty plots
          plt.plot(filtered_times[0:100], filtered_values[0:100])#first 100 as data is too large
          plt.show()
   
    #For each sensor device it returns an object containing (example below):
  """
    {
  "citations": [],
  "messages": [],
  "next": null,
  "parameters": {
    "dateFrom": "2016-09-01T00:00:00.000Z",
    "dateTo": "2016-09-01T00:01:00.000Z",
    "deviceCode": "WETLABSFLNTU2586",
    "fillGaps": true,
    "getLatest": false,
    "metaData": "Minimum",
    "method": "getByDevice",
    "outputFormat": "Array",
    "qualityControl": "clean",
    "resamplePeriod": null,
    "resampleType": null,
    "rowLimit": 100000,
    "sensorBase": null,
    "sensorsToInclude": "original",
    "token": "4289f1b9-e1cb-4cf8-b5fb-20d88dcf7eec"
  },
  "queryURL": "https://data.oceannetworks.ca/api/scalardata?deviceCode=WETLABSFLNTU2586&dateFrom=2016-09-01T00%3A00%3A00.000Z&dateTo=2016-09-01T00%3A01%3A00.000Z&method=getByDevice&token=4289f1b9-e1cb-4cf8-b5fb-20d88dcf7eec",
  "sensorData": null
}
{
  "citations": [
    {
      "citation": "Ocean Networks Canada Society. 2016. Cambridge Bay Fluorometer Turbidity Deployed 2016-08-25. Ocean Networks Canada Society. https://doi.org/10.34943/1740d05e-725e-432f-9c22-f60ced2fa508.",
      "doi": "10.34943/1740d05e-725e-432f-9c22-f60ced2fa508",
      "landingPageUrl": "https://doi.org/10.34943/1740d05e-725e-432f-9c22-f60ced2fa508",
      "queryPid": null
    }
  ],
  "messages": [],
  "next": null,
  "parameters": {
    "dateFrom": "2016-09-01T00:00:00.000Z",
    "dateTo": "2016-09-01T00:01:00.000Z",
    "deviceCode": "WETLABSFLNTUS3441",
    "fillGaps": true,
    "getLatest": false,
    "metaData": "Minimum",
    "method": "getByDevice",
    "outputFormat": "Array",
    "qualityControl": "clean",
    "resamplePeriod": null,
    "resampleType": null,
    "rowLimit": 100000,
    "sensorBase": null,
    "sensorsToInclude": "original",
    "token": "4289f1b9-e1cb-4cf8-b5fb-20d88dcf7eec"
  },
  "queryURL": "https://data.oceannetworks.ca/api/scalardata?deviceCode=WETLABSFLNTUS3441&dateFrom=2016-09-01T00%3A00%3A00.000Z&dateTo=2016-09-01T00%3A01%3A00.000Z&method=getByDevice&token=4289f1b9-e1cb-4cf8-b5fb-20d88dcf7eec",
  "sensorData": [
    {
      "actualSamples": 60,
      "data": {
        "qaqcFlags": [],
        "sampleTimes": [],
        "values": [],
      },
      "outputFormat": "array",
      "propertyCode": "chlorophyll",
      "sensorCategoryCode": "chlorophyll",
      "sensorCode": "chlorophyll",
      "sensorName": "Chlorophyll",
      "unitOfMeasure": "ug/l"
    },
    {
      "actualSamples": 60,
      "data": {
        "qaqcFlags": [],
        "sampleTimes": [],
        "values": [],
      },
      "outputFormat": "array",
      "propertyCode": "turbidityntu",
      "sensorCategoryCode": "turbidity",
      "sensorCode": "turbidity",
      "sensorName": "Turbidity",
      "unitOfMeasure": "NTU"
    }
  ]
}

    """
  