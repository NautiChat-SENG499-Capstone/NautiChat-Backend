from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VectorDocumentBase(BaseModel):
    """Shared properties of a VectorDocument."""

    model_config = ConfigDict(from_attributes=True)

    source: str = Field(..., description="Source of the document")
    usage_count: int = Field(
        ..., ge=0, description="Number of times this document was returned in searches"
    )
    uploaded_by_id: Optional[int] = Field(
        None, description="ID of the admin user who uploaded this document"
    )


class VectorDocumentOut(VectorDocumentBase):
    """What we return when reading VectorDocument metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Primary key of the vector document")


class UploadResponse(BaseModel):
    """Generic response for upload endpoints."""

    detail: str = Field(..., description="Human‑readable status message")
