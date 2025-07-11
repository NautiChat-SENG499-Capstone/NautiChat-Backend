from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from LLM.Constants.status_codes import StatusCode  # Change to LLM. for production

# from LLM.Constants.StatusCodes import StatusCode


class ObtainedParamsDictionary(BaseModel):
    """Parameters obtained from the user"""

    deviceCategoryCode: Optional[str] = None
    locationCode: Optional[str] = None
    dataProductCode: Optional[str] = None
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
    obtainedParams: Optional[ObtainedParamsDictionary] = Field(
        default_factory=ObtainedParamsDictionary
    )
    dpRequestId: Optional[int] = None
    doi: Optional[str] = (
        None  # may need to switch to a list of strings if we go through citations and make a list of all of them
    )
    citation: Optional[str] = None  # may need to switch to a list of strings
    baseUrl: Optional[str] = None
    urlParamsUsed: Optional[dict] = Field(default_factory=dict)


class ToolPlan(BaseModel):
    tool_name: str = Field(..., description="The name of the tool to use")
    inputs: Dict[str, Any] = Field(
        ..., description="Input values or descriptions of what each input is"
    )
    missing_inputs: List[str] = Field(
        ..., description="List of inputs that are missing and must be provided"
    )


class PlanningOutput(BaseModel):
    tool_plan: List[ToolPlan] = Field(
        ..., description="Tool usage plans including inputs and any missing fields"
    )
    required_inputs: Dict[str, str] = Field(
        ..., description="Explanations for each missing input parameter"
    )
