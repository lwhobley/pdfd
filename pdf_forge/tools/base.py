"""Base classes for all PDF tools."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from pdf_forge.workers.job_model import Job, JobResult


@dataclass
class ToolMeta:
    """Metadata that describes a tool for the UI registry."""
    tool_id: str
    name: str
    description: str
    category: str          # "organize" | "edit" | "convert" | "secure"
    icon: str = ""         # icon name from assets/icons/
    requires: list[str] = field(default_factory=list)  # capability names


class BaseTool:
    """Every PDF tool must subclass this and implement create_job()."""

    meta: ToolMeta

    def create_job(self, params: dict[str, Any]) -> Job:
        """Create a Job instance from user-supplied parameters.

        params keys are tool-specific. The job's input_paths list must be
        populated from params.
        """
        raise NotImplementedError

    @classmethod
    def tool_id(cls) -> str:
        return cls.meta.tool_id
