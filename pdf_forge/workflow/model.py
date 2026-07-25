"""Workflow data model — nodes, ports, connections, workflow."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any


# ── Port ─────────────────────────────────────────────────────────────────────

@dataclass
class PortSpec:
    name: str
    data_type: str   # "pdf" | "pdf_list" | "pdf_dir" | "image" | "text" | "excel" | "any"
    label: str = ""
    multiple: bool = False  # True = accepts N connections

    def display(self) -> str:
        return self.label or self.name


# ── Node spec (template) ─────────────────────────────────────────────────────

@dataclass
class NodeSpec:
    """Describes what inputs/outputs/params a node type has."""
    node_type: str
    title: str
    category: str
    inputs: list[PortSpec]
    outputs: list[PortSpec]
    param_defs: dict[str, Any] = field(default_factory=dict)  # name → default
    color: str = "#313244"


# ── Live node instance ────────────────────────────────────────────────────────

@dataclass
class WorkflowNode:
    node_type: str
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    position: tuple[float, float] = (0.0, 0.0)
    params: dict[str, Any] = field(default_factory=dict)
    label: str = ""          # user-overridable display name

    def to_dict(self) -> dict:
        return {
            "node_id":   self.node_id,
            "node_type": self.node_type,
            "position":  list(self.position),
            "params":    self.params,
            "label":     self.label,
        }

    @staticmethod
    def from_dict(d: dict) -> "WorkflowNode":
        return WorkflowNode(
            node_type=d["node_type"],
            node_id=d["node_id"],
            position=tuple(d.get("position", [0, 0])),
            params=d.get("params", {}),
            label=d.get("label", ""),
        )


# ── Connection ────────────────────────────────────────────────────────────────

@dataclass
class Connection:
    from_node: str   # node_id
    from_port: str   # port name
    to_node: str
    to_port: str

    def to_dict(self) -> dict:
        return {
            "from_node": self.from_node,
            "from_port": self.from_port,
            "to_node":   self.to_node,
            "to_port":   self.to_port,
        }

    @staticmethod
    def from_dict(d: dict) -> "Connection":
        return Connection(
            from_node=d["from_node"],
            from_port=d["from_port"],
            to_node=d["to_node"],
            to_port=d["to_port"],
        )


# ── Workflow ──────────────────────────────────────────────────────────────────

@dataclass
class Workflow:
    name: str = "Untitled Workflow"
    nodes: list[WorkflowNode] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes.append(node)

    def remove_node(self, node_id: str) -> None:
        self.nodes = [n for n in self.nodes if n.node_id != node_id]
        self.connections = [
            c for c in self.connections
            if c.from_node != node_id and c.to_node != node_id
        ]

    def add_connection(self, conn: Connection) -> None:
        # Remove any existing connection to the same input port
        self.connections = [
            c for c in self.connections
            if not (c.to_node == conn.to_node and c.to_port == conn.to_port)
        ]
        self.connections.append(conn)

    def remove_connection(self, from_node: str, from_port: str,
                          to_node: str, to_port: str) -> None:
        self.connections = [
            c for c in self.connections
            if not (c.from_node == from_node and c.from_port == from_port
                    and c.to_node == to_node and c.to_port == to_port)
        ]

    def get_node(self, node_id: str) -> WorkflowNode | None:
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def to_dict(self) -> dict:
        return {
            "version":     "1.0",
            "name":        self.name,
            "nodes":       [n.to_dict() for n in self.nodes],
            "connections": [c.to_dict() for c in self.connections],
        }

    @staticmethod
    def from_dict(d: dict) -> "Workflow":
        wf = Workflow(name=d.get("name", "Untitled Workflow"))
        wf.nodes = [WorkflowNode.from_dict(n) for n in d.get("nodes", [])]
        wf.connections = [Connection.from_dict(c) for c in d.get("connections", [])]
        return wf
