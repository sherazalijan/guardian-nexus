"""Security explanation models."""

from pydantic import BaseModel, Field


class SecurityExplanation(BaseModel):
    """Human-readable explanation generated from a risk assessment."""

    summary: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
