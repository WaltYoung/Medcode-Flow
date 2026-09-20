from __future__ import annotations

from pydantic import BaseModel, Field


class TemplateRequest(BaseModel):
    text: str = Field(..., min_length=1)


class TemplateResult(BaseModel):
    echo: str
