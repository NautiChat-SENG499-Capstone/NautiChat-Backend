from typing import Optional

from pydantic import BaseModel
from Constants.statusCodes import StatusCode #Change to LLM. for production


#from LLM.Constants.StatusCodes import StatusCode


class ObtainedParamsDictionary(BaseModel):
    """Parameters obtained from the user"""

    deviceCategoryCode: Optional[str] = None
    locationCode: Optional[str] = None
    dataProductCode: Optional[str] = None
    extension: Optional[str] = None
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None
    dpo_qualityControl: Optional[int] = 0  # default is 0, which means no qc
    dpo_resample: Optional[str] = "none"  # default is "none", which means no resampling
    dpo_dataGaps: Optional[int] = 1  # default is 1, which means data gaps are included


class RunConversationResponse(BaseModel):
    """Response from running a conversation with the LLM"""

    status: StatusCode
    response: str
    obtainedParams: Optional[ObtainedParamsDictionary] = {}
    dpRequestId: Optional[int] = None
    doi: Optional[str] = None  #may need to switch to a list of strings if we go through citations and make a list of all of them
    citation: Optional[str] = None  #may need to switch to a list of strings
    baseUrl: Optional[str] = None
    urlParamsUsed: Optional[ObtainedParamsDictionary] = {}