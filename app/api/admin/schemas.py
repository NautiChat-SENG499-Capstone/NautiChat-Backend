from typing import Annotated, Optional

from fastapi import File, Form, UploadFile
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

    id: int = Field(..., description="Primary key of the vector document")


class UploadResponse(BaseModel):
    """Generic response for upload endpoints."""

    detail: str = Field(..., description="Human‑readable status message")


class RawTextUploadRequest(BaseModel):
    source: Annotated[str, Form(...)]
    input_text: Annotated[str, Form(...)]

    @classmethod
    def as_form(
        cls,
        source: Annotated[str, Form(...)],
        input_text: Annotated[str, Form(...)],
    ) -> "RawTextUploadRequest":
        return cls(source=source, input_text=input_text)


class PDFUploadRequest(BaseModel):
    source: Annotated[str, Form(...)]
    file: Annotated[UploadFile, File(...)]

    @classmethod
    def as_form(
        cls,
        source: Annotated[str, Form(...)],
        file: Annotated[UploadFile, File(...)],
    ) -> "PDFUploadRequest":
        return cls(source=source, file=file)


class JSONUploadRequest(BaseModel):
    source: Annotated[str, Form(...)]
    file: Annotated[UploadFile, File(...)]

    @classmethod
    def as_form(
        cls,
        source: Annotated[str, Form(...)],
        file: Annotated[UploadFile, File(...)],
    ) -> "JSONUploadRequest":
        return cls(source=source, file=file)
