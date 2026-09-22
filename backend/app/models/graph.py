
"""Models used by Guardian Nexus graph orchestration."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class NodeStatus(StrEnum):
    """Execution status for a graph node."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class GraphError(BaseModel):
    """Structured error captured during graph execution."""

    node: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class CandidateTarget(BaseModel):
    """A target identified for optional threat-intelligence lookup."""

    target_type: str = Field(min_length=1)
    value: str = Field(min_length=1)
    source: str = Field(min_length=1)
