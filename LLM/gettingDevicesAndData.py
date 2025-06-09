from onc import ONC
import json
import matplotlib.pyplot as plt

async def get_devices_info(hasIfsEqual = False, ifEqualKey = None, ifEqualKeyValue = None, hasIfsIn = False, ifInKey = None, ifInKeyValue = None):
    """Get devices based on the provided parameters."""
    onc = ONC("4289f1b9-e1cb-4cf8-b5fb-20d88dcf7eec")
    params = {
        "locationCode": "CBYIP",
        #"deviceName": "oxygen",
    }
    deviceInfo = []
    devices = onc.getDevices(params)
    # print("getting devices")
    for device in devices:
      if hasIfsEqual:
        # print("hasIfsEqual is True")
        # print("ifEqualKey:", ifEqualKey)
        # print("ifEqualKeyValue:", ifEqualKeyValue)
        if (["True", "true"] in ifEqualKeyValue):
          ifEqualKeyValue = True
        elif (["False", "false"] in ifEqualKeyValue):
          ifEqualKeyValue = False
        if device[ifEqualKey] == ifEqualKeyValue:
          deviceInfo.append({"deviceCode": device["deviceCode"], "dataRating": device["dataRating"]})
      elif hasIfsIn:
        # print("hasIfsIn is True")
        # print("ifInKey:", ifInKey)
        # print("ifInKeyValue:", ifInKeyValue)
        if ifInKeyValue.lower() in device[ifInKey].lower():
          deviceInfo.append({"deviceCode": device["deviceCode"], "dataRating": device["dataRating"]})
      else:
        deviceInfo.append({"deviceCode": device["deviceCode"], "dataRating": device["dataRating"]})
    # print("return deviceInfo")
    return deviceInfo
    #return json.dumps(deviceInfo) #dont know if need to convert to JSON. Want it to be a string if just need this to be returned but if need for an additional function I dont want it to be a string.


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

async def get_scalar_data_by_device(deviceInfo):
  onc = ONC("4289f1b9-e1cb-4cf8-b5fb-20d88dcf7eec")
  ScalarData=[]
  if(type(deviceInfo) is str):
    print("deviceInfo is a string, converting to JSON")
    deviceInfo = json.loads(deviceInfo)
    print("deviceInfo:", deviceInfo)
    deviceInfo = deviceInfo["deviceInfo"] if "deviceInfo" in deviceInfo else deviceInfo
    print("deviceInfo after conversion:", deviceInfo)
  print("deviceInfo:", deviceInfo)
  for device in deviceInfo:
    for samplePeriod in device["dataRating"]:
      params = {
        "deviceCode": device["deviceCode"],
        "dateFrom": samplePeriod["dateFrom"],
        "dateTo": samplePeriod["dateTo"],
      }
      scalarData = onc.getScalardata(params)
      #print("getting scalar data")
      if("sensorData" in scalarData and scalarData["sensorData"] is not None):
        for sensorData in scalarData["sensorData"]:
          filtered_times = [t for l, t in zip(sensorData["data"]["qaqcFlags"], sensorData["data"]["sampleTimes"]) if l == 1]#If l!=1 then it is invalid data or NaN (missing data)
          filtered_values = [t for l, t in zip(sensorData["data"]["qaqcFlags"], sensorData["data"]["values"]) if l == 1]
          if(len(filtered_times)>0): #So not making empty plots
            ScalarData.append({"deviceCode": device["deviceCode"], "data": {"sampleTimes": filtered_times, "values": filtered_values}})

  #print("return ScalarData")
  return json.dumps(ScalarData)

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
 
#deviceInfo = get_devices_info_by_params(hasIfsIn=True, ifInKey="deviceName", ifInKeyValue="OXYGEN")