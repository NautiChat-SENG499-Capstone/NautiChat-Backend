from datetime import datetime
from typing import Optional

from onc import ONC

from LLM.Constants.status_codes import StatusCode
from LLM.Constants.utils import resample_periods, sync_param
from LLM.schemas import ObtainedParamsDictionary

ROW_LIMIT = "8000"


async def get_scalar_data(
    user_onc_token: str,
    deviceCategoryCode: Optional[str] = None,
    locationCode: Optional[str] = None,
    propertyCode: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    obtainedParams: ObtainedParamsDictionary = None,
):
    if obtainedParams is None:
        obtainedParams = ObtainedParamsDictionary()
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
    locationCode = sync_param(
        "locationCode", locationCode, obtainedParams, allObtainedParams
    )
    propertyCode = sync_param(  # uses dataProductCode of ObtainedParams dict to not overload core.py
        "dataProductCode", propertyCode, obtainedParams, allObtainedParams
    )
    dateFrom = sync_param("dateFrom", dateFrom, obtainedParams, allObtainedParams)
    dateTo = sync_param("dateTo", dateTo, obtainedParams, allObtainedParams)
    print(f"Obtained parameters: {allObtainedParams}")

    resample_period = 1
    if dateFrom and dateTo:
        begin = datetime.fromisoformat(dateFrom.replace("Z", "+00:00"))
        end = datetime.fromisoformat(dateTo.replace("Z", "+00:00"))

        delta_seconds = (end - begin).total_seconds()

        resample_period = min(resample_periods, key=lambda x: abs(x - (delta_seconds)))

    allParamsNeeded = {
        "deviceCategoryCode": deviceCategoryCode,
        "dateFrom": dateFrom,
        "dateTo": dateTo,
        "locationCode": locationCode,
        "propertyCode": propertyCode,
        "resampleType": "avgMinMax",
        "resamplePeriod": resample_period,
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
        param_keys = ", ".join(
            k if k != "dataProductCode" else "propertyCode"
            for k, v in allObtainedParams.items()
            if v != ""
        )
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
        if response["sensorData"]:
            return {
                "response": response,
                "description": f"Here is the minimum/maximum/average scalar data you requested from the {deviceCategoryCode} at Cambridge Bay with location code: {locationCode} from {begin} to {end}",
                "status": StatusCode.REGULAR_MESSAGE,
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location?",
                "urlParamsUsed": allParamsNeeded,
            }
        else:
            return {
                "response": response,
                "description": f"There is no scalar data at {deviceCategoryCode} at Cambridge Bay with location code: {locationCode} from {begin} to {end}.",
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
