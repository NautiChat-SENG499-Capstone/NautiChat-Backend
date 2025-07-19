# from LLM.Constants.StatusCodes import StatusCode
import json
import re
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field, ValidationError

from LLM.Constants.status_codes import StatusCode  # Change to LLM. for production

T = TypeVar("T", bound=BaseModel)


def parse_llm_response(
    raw_response: str,
    model: Type[T],
    extract_json: bool = True,
) -> T:
    """
    Parse a raw LLM response string into a Pydantic model instance.

    Args:
        raw_response: The raw string response from the LLM.
        model: The Pydantic model class to parse into.
        extract_json: If True, try to extract JSON substring from raw text.
        ex)tool_call_list = parse_llm_response(response_text, ToolCallList)

    Returns:
        An instance of the provided Pydantic model.

    Raises:
        ValueError: If JSON parsing or validation fails.
    """
    try:
        json_text = raw_response
        if extract_json:
            # Attempt to extract JSON object from text (if wrapped in extra text)
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if not match:
                raise ValueError("No JSON object found in the response text.")
            json_text = match.group(0)

        data = json.loads(json_text)
        return model.model_validate(data)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    except ValidationError as e:
        raise ValueError(f"Model validation error: {e}")


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
    obtained_params: Optional[ObtainedParamsDictionary] = Field(
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


class PlanningResponse(BaseModel):
    tools_needed: bool = Field(
        ...,
        description="True if one or more tools need to be called, false if none are required.",
    )
    reasoning: str = Field(
        ...,
        description="Natural language explanation for whether tools are needed, which tools to use if any, and what inputs are needed for each tool.",
    )
    inputs_provided: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "A dictionary where keys are 'tool_name.input_name' and values are natural language descriptions of inputs are already provided by the user or current context."
        ),
    )
    inputs_missing: Dict[str, str] = (
        Field(
            default_factory=dict,
            description=(
                "A dictionary where keys are 'tool_name.input_name' and values are natural language descriptions of inputs that are missing and need to be retrieved (e.g., by querying a vector DB)."
            ),
        ),
    )
    inputs_uncertain: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Inputs that might be inferred or partially present in the user's input, but are not confidently resolved. Should be confirmed or refined before using."
        ),
    )


class ToolCall(BaseModel):
    name: str = Field(
        ...,
        description="The name of the tool to be called.",
    )
    id: int = Field(
        ...,
        description="A unique identifier for the tool call, used to track the call in the conversation.",
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="The parameters to pass to the tool. The key should be the parameter name, and the value should be the value to pass.",
    )


class ToolCallList(BaseModel):
    tools: List[ToolCall] = Field(
        default_factory=list,
        description="A list of tools the model wants to call with input parameters.",
    )
