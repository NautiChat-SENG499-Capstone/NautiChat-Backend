from datetime import datetime
from typing import Optional

from onc import ONC

from LLM.Constants.scalar_data import scalarData
from LLM.Constants.status_codes import StatusCode
from LLM.Constants.utils import resample_periods, sync_param
from LLM.schemas import ObtainedParamsDictionary

ROW_LIMIT = "100"


def find_possible_property_codes(deviceCategoryCode: str) -> list[str]:
    """Finds possible property codes for a given device category code."""
    possible_property_codes = []
    for device in scalarData:
        if device["deviceCategoryCode"] == deviceCategoryCode:
            possible_property_codes.extend(device["possiblePropertyCodes"])
    return possible_property_codes


def obtain_location_codes(deviceCategoryCode: str) -> list[str]:
    locationCodes = []
    for device in scalarData:
        if device["deviceCategoryCode"] == deviceCategoryCode:
            locationCodes.append(device["locationCode"])
    return locationCodes


async def get_scalar_data(
    user_onc_token: str,
    deviceCategoryCode: Optional[str] = None,
    locationCode: Optional[str] = None,
    propertyCode: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    obtainedParams: ObtainedParamsDictionary = ObtainedParamsDictionary(),
):
    onc = ONC(user_onc_token)
    """
        Get the deviceCategoryCode at a certain locationCode at Cambridge Bay in a propertyCode with a resamplePeriod and resampleType,
        so that users can request scalar data, over a specified time period.
        Returns the result of a scalar data request.

        This function performs a data request to the ONC API, then returns the data to the LLM.
        If this function is called, the LLM will only provide the parameters the user has explicitly given.
        DO NOT guess, assume, or invent any parameters.
        DO NOT add any parameters unless they're explicitly given.
        If parameters are missing, the function will handle asking the user for them.
        If there that device isn't deployed at that time, the LLM will respond with the deployment times.
        If there is no data from the device during a deployed time, the LLM will tell the user, and not invent data.

        Returns:
            result (str): The result of the data request.

        Args:
            deviceCategoryCode (str): An ONC-defined code identifying the type of device 
            locationCode (str): An ONC-defined code identifying the location of the device 
            propertyCode (str): An ONC-defined code identifying the type of data being requested 
            dateFrom (str): The start date of the data request in ISO 8601 format 
            dateTo (str): The end date of the data request in ISO 8601 format 
    """
    allObtainedParams = {}
    deviceCategoryCode = sync_param(
        "deviceCategoryCode", deviceCategoryCode, obtainedParams, allObtainedParams
    )

    propertyCode = sync_param(
        "propertyCode", propertyCode, obtainedParams, allObtainedParams
    )
    if propertyCode is None and deviceCategoryCode is not None:
        propertyCodes = find_possible_property_codes(
            deviceCategoryCode
        )  # finding property Code and if there are no property codes then that also means there is no data for that device category code
        if len(propertyCodes) == 0:
            return {
                "status": StatusCode.NO_DATA,
                "response": f"Hey! It looks like you are requesting scalar data! Unfortunately, I don't have any property codes for the {deviceCategoryCode} at Cambridge Bay. Therefore, I cannot complete the scalar data request for this device. ",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            }
        elif len(propertyCodes) == 1:
            propertyCode = sync_param(
                "propertyCode", propertyCodes[0], obtainedParams, allObtainedParams
            )
        else:
            return {
                "status": StatusCode.PARAMS_NEEDED,
                "response": f"Hey! It looks like you are requesting scalar data! I have multiple property codes for the {deviceCategoryCode} at Cambridge Bay. Please provide a property code from the following list: {', '.join(propertyCodes)}.",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            }

    locationCode = sync_param(
        "locationCode", locationCode, obtainedParams, allObtainedParams
    )
    if locationCode is None and deviceCategoryCode is not None:
        locationCodes = obtain_location_codes(deviceCategoryCode)
        if len(locationCodes) == 0:
            return {
                "status": StatusCode.NO_DATA,
                "response": f"Error: No location codes found for device category code '{deviceCategoryCode}'. Please select a different device category code or check the available location codes.",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            }
        elif len(locationCodes) == 1:
            locationCode = locationCodes[0]
            locationCode = sync_param(
                "locationCode", locationCode, obtainedParams, allObtainedParams
            )
        else:  # If there are multiple location codes, return them to the user
            return {
                "status": StatusCode.PARAMS_NEEDED,
                "response": f"Hey! It looks like you want scalar data! However, I found multiple location codes for device category code '{deviceCategoryCode}': {', '.join(locationCodes)}. Please specify which one you want to use.",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            }

    dateFrom = sync_param("dateFrom", dateFrom, obtainedParams, allObtainedParams)
    dateTo = sync_param("dateTo", dateTo, obtainedParams, allObtainedParams)
    print(f"Obtained parameters: {allObtainedParams}")

    resample_period = 1
    if dateFrom and dateTo:
        begin = datetime.fromisoformat(dateFrom.replace("Z", "+00:00"))
        end = datetime.fromisoformat(dateTo.replace("Z", "+00:00"))

        delta_seconds = (end - begin).total_seconds()

        resample_period = min(resample_periods, key=lambda x: abs(x - (delta_seconds)))
        print(f"Resample period determined: {resample_period}")

    allParamsNeeded = {
        "deviceCategoryCode": deviceCategoryCode,
        "dateFrom": dateFrom,
        "dateTo": dateTo,
        "locationCode": locationCode,
        "propertyCode": propertyCode,
        "resampleType": "avgMinMax",
        "resamplePeriod": str(resample_period),
        "outputFormat": "object",
        "rowLimit": ROW_LIMIT,
        "token": user_onc_token,
    }  # Only the necessary parameters for a data download request.
    neededParams = [
        param
        for param, value in allParamsNeeded.items()
        if value is None or value == ""
    ]  # List of paramaters that are needed but not set.

    if len(neededParams) > 0:  # If need one or more parameters
        print("OBTAINED PARAMS: ", ObtainedParamsDictionary(**allObtainedParams))
        param_keys = ", ".join(k for k, v in allObtainedParams.items() if v != "")
        if param_keys == "":
            return {
                "status": StatusCode.PARAMS_NEEDED,
                "response": f"Hey! It looks like you are requesting scalar data! I don't have any parameters so far. I still need you to please provide the following missing parameters so I can complete the scalar data request: {', '.join(neededParams)}. Thank you!",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
                "urlParamsUsed": allParamsNeeded,
            }
        else:
            return {
                "status": StatusCode.PARAMS_NEEDED,
                "response": f"Hey! It looks like you are requesting scalar data! So far I have the following parameters: {param_keys}. However, I still need you to please provide the following missing parameters so I can complete the scalar data request: {', '.join(neededParams)}. Thank you!",
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
                "urlParamsUsed": allParamsNeeded,
            }

    try:
        response = onc.getScalardataByLocation(allParamsNeeded)
        print(f"Response from ONC: {response}")
        datetimedateFrom = datetime.strptime(dateFrom, "%Y-%m-%dT%H:%M:%S.%fZ")
        datetimedateTo = datetime.strptime(dateTo, "%Y-%m-%dT%H:%M:%S.%fZ")
        begin = datetimedateFrom.strftime("%B %d, %Y at %I:%M%p")
        end = datetimedateTo.strftime("%B %d, %Y at %I:%M%p")
        print("RESPONSE FROM ONC: ", response)
        if response["sensorData"]:
            return {
                "response": {
                    "description": f"Here is the minimum/maximum/average scalar data you requested from the {deviceCategoryCode} at Cambridge Bay with location code: {locationCode} from {begin} to {end}",
                    "data": {
                        "minimum": response["sensorData"][0]["data"][0]["minimum"],
                        "Time of minimum value obtained": response["sensorData"][0][
                            "data"
                        ][0]["minTime"],
                        "maximum": response["sensorData"][0]["data"][0]["maximum"],
                        "Time of maximum value obtained": response["sensorData"][0][
                            "data"
                        ][0]["maxTime"],
                        "average": response["sensorData"][0]["data"][0]["value"],
                    },
                },
                "status": StatusCode.REGULAR_MESSAGE,
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
                "urlParamsUsed": allParamsNeeded,
            }
        else:
            return {
                "response": f"There is no scalar data at {deviceCategoryCode} at Cambridge Bay with location code: {locationCode} from {begin} to {end}.",
                "status": StatusCode.NO_DATA,
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
                "urlParamsUsed": allParamsNeeded,
            }
    except Exception as e:
        error_message = str(e)
        if "API Error 127" in error_message:
            deploymentParams = {
                "locationCode": allObtainedParams["locationCode"],
                "deviceCategoryCode": allObtainedParams["deviceCategoryCode"],
            }
            deployments = onc.getDeployments(deploymentParams)
            deployment_ranges = [
                {"begin": d["begin"], "end": d["end"]}
                for d in deployments
                if "begin" in d and "end" in d
            ]
            deployment_string = ""
            for deployment_range in deployment_ranges:
                if deployment_range["begin"] and deployment_range["end"]:
                    zbegin = datetime.fromisoformat(
                        deployment_range["begin"].replace("Z", "+00:00")
                    )
                    zend = datetime.fromisoformat(
                        deployment_range["end"].replace("Z", "+00:00")
                    )
                    begin = zbegin.strftime("%B {day}, %Y at %I:%M%p").format(
                        day=zbegin.day
                    )
                    end = zend.strftime("%B {day}, %Y at %I:%M%p").format(day=zend.day)
                    deployment_string += f"Begin: {begin}, End: {end}\n"
            allObtainedParams["dateTo"] = ""
            allObtainedParams["dateFrom"] = ""
            return {
                "response": f"Device was not deployed during the requested period. Here are the periods that {deviceCategoryCode} at {locationCode} has been deployed:\n{deployment_string}",
                "status": StatusCode.DEPLOYMENT_ERROR,
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
                "urlParamsUsed": allParamsNeeded,
            }
        else:
            return {
                "status": StatusCode.SCALAR_REQUEST_ERROR,
                "response": f"Error: {str(e)}",
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
                "urlParamsUsed": allParamsNeeded,
            }
