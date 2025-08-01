from typing import Optional

from pydantic import BaseModel, Field

from LLM.Constants.status_codes import StatusCode  # Change to LLM. for production

# from LLM.Constants.StatusCodes import StatusCode


class ToolCall(BaseModel):
    """function name, arguments and response from the tool"""

    function_name: str
    arguments: str
    response: str


class ObtainedParamsDictionary(BaseModel):
    """Parameters obtained from the user"""

    deviceCategoryCode: Optional[str] = None
    locationCode: Optional[str] = None
    dataProductCode: Optional[str] = None
    propertyCode: Optional[str] = None
    extension: Optional[str] = None
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None
    dpo_qualityControl: Optional[int] = (
        1  # default is 1, which means data points with qc failures are removed
    )
    dpo_dataGaps: Optional[int] = 1  # default is 1, which means data gaps are included
    dpo_resample: Optional[str] = "none"  # default is "none", which means no resampling
    dpo_minMax: Optional[int] = (
        None  # default is None, which means n period set foro min/max resampling
    )
    dpo_average: Optional[int] = (
        None  # default is None, which means no period set for average resampling
    )
    dpo_minMaxAvg: Optional[int] = (
        None  # default is None, which means no period set for min/max/average resampling (Default is 60)
    )


class RunConversationResponse(BaseModel):
    """Response from running a conversation with the LLM"""

    status: StatusCode
    response: str
    obtainedParams: ObtainedParamsDictionary = Field(
        default_factory=ObtainedParamsDictionary
    )
    dpRequestId: Optional[int] = None
    doi: Optional[str] = (
        None  # may need to switch to a list of strings if we go through citations and make a list of all of them
    )
    citation: Optional[str] = None  # may need to switch to a list of strings
    baseUrl: Optional[str] = None
    urlParamsUsed: Optional[dict] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    point_ids: list[str] = Field(default_factory=list)
