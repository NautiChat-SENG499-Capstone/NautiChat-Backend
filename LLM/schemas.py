from typing import Optional

from LLM.Constants.StatusCodes import StatusCode
from pydantic import BaseModel









class ObtainedParamsDictionary(BaseModel):
    """Parameters obtained from the user"""

    deviceCategoryCode: Optional[str] = None     
    locationCode: Optional[str] = None  
    dataProductCode: Optional[str] = None
    extension: Optional[str] = None     
    dateFrom: Optional[str] = None  
    dateTo: Optional[str] = None # super long comment for no reason reason no reason reason reason reason no reason no reason long comment
    dpo_qualityControl: Optional[int] = 0  # default is 0, which means no qc
    dpo_resample: Optional[str] = "none"  # default is "none", which means no resampling
    dpo_dataGaps: Optional[int] = 1  # default is 1, which means data gaps are included


class RunConversationResponse(BaseModel):
    """Response from running a conversation with the LLM"""

    status: StatusCode
    response: str
    obtainedParams: Optional[ObtainedParamsDictionary] = None
    dpRequestId: Optional[int] = None
    # may need to switch to a list of strings if we go through citations and make a list of all of them
    doi: Optional[str] = None
    citation: Optional[str] = None  # may need to switch to a list of strings
