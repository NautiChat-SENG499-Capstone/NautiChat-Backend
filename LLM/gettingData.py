from onc import ONC
import json

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


params = {
    "locationCode": "CBYIP",
}
devices = onc.getDevices(params)
for device in devices:
    if "description" in device:
        print(f"Device Name: {device['deviceName']}")
        print(f"Description: {device['description']}")
# dev1Code = devices[0]["deviceCategoryCode"]
# print(dev1Code)
# params = {
#     "deviceCategoryCode": dev1Code,
# }
# dev1 = onc.getDevices(params)
# print(json.dumps(dev1, indent=2))


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

# params = {
#     "description": "doppler",
# }
# catDesc = onc.getDeviceCategories(params)
# print(json.dumps(catDesc, indent=2))
