"""Workflow DAG — validation, topological sort, and execution."""
from __future__ import annotations
import os
import tempfile
import logging
from collections import defaultdict, deque
from typing import Callable

from pdf_forge.workflow.model import Workflow, WorkflowNode, Connection
from pdf_forge.workflow.node_registry import get_spec

log = logging.getLogger(__name__)


class GraphError(Exception):
    pass


def validate(workflow: Workflow) -> list[str]:
    """Return list of validation error strings (empty = valid)."""
    errors: list[str] = []
    ids = {n.node_id for n in workflow.nodes}

    for conn in workflow.connections:
        if conn.from_node not in ids:
            errors.append(f"Connection references missing node {conn.from_node}")
        if conn.to_node not in ids:
            errors.append(f"Connection references missing node {conn.to_node}")

    # Check for cycles
    try:
        topological_sort(workflow)
    except GraphError as e:
        errors.append(str(e))

    # Check required inputs
    connected_inputs: set[tuple[str, str]] = {
        (c.to_node, c.to_port) for c in workflow.connections
    }
    for node in workflow.nodes:
        spec = get_spec(node.node_type)
        if not spec:
            errors.append(f"Unknown node type: {node.node_type}")
            continue
        for port in spec.inputs:
            if not port.multiple and (node.node_id, port.name) not in connected_inputs:
                # Source nodes don't need file connections — they use params
                if node.node_type not in ("source",):
                    errors.append(
                        f"Node '{spec.title}' [{node.node_id}]: "
                        f"input port '{port.name}' is not connected"
                    )

    return errors


def topological_sort(workflow: Workflow) -> list[str]:
    """Kahn's algorithm. Returns node_ids in execution order."""
    in_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, list[str]] = defaultdict(list)

    for node in workflow.nodes:
        in_degree.setdefault(node.node_id, 0)

    for conn in workflow.connections:
        adjacency[conn.from_node].append(conn.to_node)
        in_degree[conn.to_node] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbor in adjacency[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(workflow.nodes):
        raise GraphError("Workflow contains a cycle")
    return order


class WorkflowExecutor:
    """Execute a workflow, passing file paths through connections.

    progress_cb(node_id, pct): called with per-node progress 0–100
    log_cb(node_id, msg): called with log messages
    Each node's tool job is executed synchronously on the calling thread
    (the caller should run this in a WorkerThread).
    """

    def __init__(
        self,
        workflow: Workflow,
        output_dir: str,
        cancel_flag_ref: list[bool] | None = None,
        progress_cb: Callable[[str, int], None] | None = None,
        log_cb: Callable[[str, str], None] | None = None,
    ) -> None:
        self._wf = workflow
        self._output_dir = output_dir
        self._cancel = cancel_flag_ref or [False]
        self._progress = progress_cb or (lambda nid, pct: None)
        self._log = log_cb or (lambda nid, msg: None)

    def execute(self) -> dict[str, list[str]]:
        """Run the workflow; return {node_id: [output_paths]}."""
        errors = validate(self._wf)
        if errors:
            raise GraphError("Validation failed:\n" + "\n".join(errors))

        order = topological_sort(self._wf)
        os.makedirs(self._output_dir, exist_ok=True)

        # Map (node_id, port_name) → list[str] of file paths, used for wiring
        outputs: dict[tuple[str, str], list[str]] = {}
        # Every node's results, including sinks (which have no output ports)
        produced: dict[str, list[str]] = {}

        for step, node_id in enumerate(order):
            if self._cancel[0]:
                raise GraphError("Cancelled")

            node = self._wf.get_node(node_id)
            assert node is not None
            self._log(node_id, f"Executing {node.node_type}")
            self._progress(node_id, 0)

            result_paths = self._run_node(node, outputs)
            produced[node_id] = result_paths

            spec = get_spec(node.node_type)
            if spec and spec.outputs:
                out_port = spec.outputs[0].name
                outputs[(node_id, out_port)] = result_paths

            self._progress(node_id, 100)
            self._log(node_id, f"Done → {result_paths}")

        return produced

    def _run_node(
        self,
        node: WorkflowNode,
        outputs: dict[tuple[str, str], list[str]],
    ) -> list[str]:
        from pdf_forge.tools.registry import registry

        # Gather inputs from connected upstream nodes
        def get_input(port_name: str) -> list[str]:
            paths = []
            for conn in self._wf.connections:
                if conn.to_node == node.node_id and conn.to_port == port_name:
                    upstream = outputs.get((conn.from_node, conn.from_port), [])
                    paths.extend(upstream)
            return paths

        params = dict(node.params)
        spec = get_spec(node.node_type)
        if not spec:
            raise GraphError(f"Unknown node type: {node.node_type}")

        # ── Source node ───────────────────────────────────────────────────
        if node.node_type == "source":
            path = params.get("file_path", "")
            if not path or not os.path.exists(path):
                raise GraphError(f"Source node: file not found: {path}")
            return [path]

        # ── Sink node ─────────────────────────────────────────────────────
        if node.node_type == "sink":
            inputs = get_input("input")
            if not inputs:
                raise GraphError("Sink node: no input connected")
            out_path = params.get("output_path", "")
            if not out_path:
                out_path = self._auto_output(node.node_id, inputs[0], ".pdf")
            import shutil
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            shutil.copy2(inputs[0], out_path)
            return [out_path]

        # ── Regular tool node ─────────────────────────────────────────────
        tool = registry.get(node.node_type)
        if not tool:
            raise GraphError(f"Tool not registered: {node.node_type}")

        # Build the job params dict
        job_params = dict(params)

        if spec.inputs:
            first_port = spec.inputs[0]
            inp = get_input(first_port.name)
            if first_port.multiple:
                job_params["input_paths"] = inp
            elif inp:
                job_params["input_path"] = inp[0]

        # Determine output path(s)
        if spec.outputs:
            out_port = spec.outputs[0]
            if out_port.data_type in ("image", "pdf_dir"):
                out_dir = os.path.join(self._output_dir, node.node_id)
                os.makedirs(out_dir, exist_ok=True)
                job_params["output_dir"] = out_dir
            elif out_port.data_type in ("text", "excel"):
                ext = ".txt" if out_port.data_type == "text" else ".xlsx"
                job_params["output_path"] = self._auto_output(
                    node.node_id,
                    job_params.get("input_path", "input"),
                    ext,
                )
            else:
                if "output_path" not in job_params:
                    job_params["output_path"] = self._auto_output(
                        node.node_id,
                        job_params.get("input_path", "input"),
                        ".pdf",
                    )

        job = tool.create_job(job_params)
        job.set_callbacks(
            lambda pct: self._progress(node.node_id, pct),
            lambda msg: self._log(node.node_id, msg),
        )
        result = job.execute()
        return result.output_paths

    def _auto_output(self, node_id: str, input_path: str, ext: str) -> str:
        stem = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(self._output_dir, f"{stem}_{node_id}{ext}")
