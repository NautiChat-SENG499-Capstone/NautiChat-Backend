from typing import Optional #,List

from pydantic import BaseModel

class RunConversationResponse(BaseModel):
    """Response from running a conversation with the LLM"""
    status: int
    response: str
    obtainedParams: Optional[dict] = None
    dpRequestId: Optional[str] = None
    doi: Optional[str] = None  #may need to switch to a list of strings if we go through citations and make a list of all of them
    citation: Optional[str] = None  #may need to switch to a list of strings



    
