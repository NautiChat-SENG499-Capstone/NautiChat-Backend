from datetime import datetime
from typing import Optional

from onc import ONC

from LLM.Constants.status_codes import StatusCode
from LLM.Constants.utils import sync_param
from LLM.schemas import ObtainedParamsDictionary
from LLM.tools_sprint1 import get_deployed_devices_over_time_interval

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
        Do not guess, assume, or invent any missing parameters.
        If parameters are missing, the function will handle asking the user for them.
        If there that device isn't deployed at that time, the LLM will respond with the deployment times.
        If there is no data from the device during a deployed time, the LLM will tell the user, and not invent data.

        Returns:
            result (str): The result of the data request.

        Args:
            deviceCategoryCode (str): An ONC-defined code identifying the type of device 
                                    (e.g., DIVE_COMPUTER, NAV, ROV_CAMERA, ACOUSTICRECEIVER, ADCP1200KHZ).
            locationCode (str): An ONC-defined code identifying the location of the device 
                                (e.g., 'CBYDS' for the Cambridge Bay Diver data or 'CBYIP' for the Cambridge Bay Underwater Network or 'CBYSP' for the Cambridge Bay Safe Passage Buoy or 'CBYSS' for the Cambridge Bay Shore Station).
            propertyCode (str): An ONC-defined code identifying the type of data being requested 
                                (e.g., 'oxygen' for oxygen data, 'temperature' for temperature data).
            dateFrom (str): The start date of the data request in ISO 8601 format 
                            (e.g., '2016-06-01T00:00:00.000Z'). (YYYY-MM-DDTHH:MM:SS.sssZ)
            dateTo (str): The end date of the data request in ISO 8601 format 
                          (e.g., '2016-09-30T23:59:59.999Z'). (YYYY-MM-DDTHH:MM:SS.sssZ)
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

    resample_periods = [
        1,
        5,
        10,
        15,
        30,
        60,
        300,
        600,
        900,
        1800,
        3600,
        7200,
        14400,
        21600,
        43200,
        86400,
        172800,
        259200,
        604800,
        1209600,
        2592000,
    ]
    resample_period = 1
    if dateFrom and dateTo:
        begin = datetime.fromisoformat(dateFrom.replace("Z", "+00:00"))
        end = datetime.fromisoformat(dateTo.replace("Z", "+00:00"))

        delta_seconds = (end - begin).total_seconds()

        resample_period = min(
            resample_periods, key=lambda x: abs(x - (delta_seconds / 10))
        )

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
    }  # Only the necessary parameters for a data download request.
    neededParams = [
        param for param, value in allParamsNeeded.items() if value is None
    ]  # List of paramaters that are needed but not set.

    if len(neededParams) > 0:  # If need one or more parameters
        print("OBTAINED PARAMS: ", ObtainedParamsDictionary(**allObtainedParams))
        param_keys = ", ".join(
            k if k != "dataProductCode" else "propertyCode"
            for k in allObtainedParams.keys()
        )
        return {
            "status": StatusCode.PARAMS_NEEDED,
            "response": f"Hey! It looks like you are requesting scalar data! So far I have the following parameters: {param_keys}. However, I still need you to please provide the following missing parameters so I can complete the scalar data request: {', '.join(neededParams)}. Thank you!",
            "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
            "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location",
        }

    try:
        response = onc.getScalardataByLocation(allParamsNeeded)
        print(f"Response from ONC: {response}")
        if response["sensorData"]:
            return {
                "response": response,
                "description": f"Here is the scalar data you requested from the {deviceCategoryCode} at {locationCode} from {dateFrom} to {dateTo}",
                "status": StatusCode.REGULAR_MESSAGE,
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location",
            }
        else:
            return {
                "response": response,
                "description": f"There is no scalar data at {deviceCategoryCode} at {locationCode} from {dateFrom} to {dateTo}.",
                "status": StatusCode.NO_DATA,
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location",
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
                zbegin = datetime.fromisoformat(
                    deployment_range["begin"].replace("Z", "+00:00")
                )
                zend = datetime.fromisoformat(
                    deployment_range["end"].replace("Z", "+00:00")
                )
                begin = zbegin.strftime("%B {day}th, %Y at %I:%M%p").format(
                    day=zbegin.day
                )
                end = zend.strftime("%B {day}th, %Y at %I:%M%p").format(day=zend.day)
                deployment_string += f"Begin: {begin}, End: {end}\n"
            allObtainedParams["dateTo"] = ""
            allObtainedParams["dateFrom"] = ""
            return {
                "response": f"Device was not deployed during the requested period. Here are the periods that that device has been deployed:\n{deployment_string}",
                "status": StatusCode.DEPLOYMENT_ERROR,
                "obtainedParams": ObtainedParamsDictionary(**allObtainedParams),
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location",
            }
        else:
            return {
                "status": StatusCode.LLM_ERROR,
                "response": f"Error: {str(e)}",
                "baseUrl": "https://data.oceannetworks.ca/api/scalardata/location",
            }
