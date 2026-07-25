"""Workflow JSON serialization."""
from __future__ import annotations
import json
import os
from pdf_forge.workflow.model import Workflow


def save(workflow: Workflow, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(workflow.to_dict(), f, indent=2)


def load(path: str) -> Workflow:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Workflow.from_dict(data)
