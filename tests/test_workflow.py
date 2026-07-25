"""Tests for M5 — workflow model, DAG, serialization, and execution."""
from __future__ import annotations
import json
import os
import tempfile
import pytest

from pdf_forge.workflow.model import (
    Workflow, WorkflowNode, Connection, PortSpec, NodeSpec,
)
from pdf_forge.workflow.graph import (
    validate, topological_sort, WorkflowExecutor, GraphError,
)
from pdf_forge.workflow.node_registry import get_spec, all_specs, specs_by_category
from pdf_forge.workflow import serializer


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _two_node_wf(src_path: str = "/tmp/a.pdf", out_path: str = "") -> Workflow:
    """source → sink workflow."""
    wf = Workflow(name="Test WF")
    src = WorkflowNode(node_type="source", node_id="n1", params={"file_path": src_path})
    snk = WorkflowNode(node_type="sink",   node_id="n2", params={"output_path": out_path})
    wf.add_node(src)
    wf.add_node(snk)
    wf.add_connection(Connection("n1", "output", "n2", "input"))
    return wf


def _make_pdf(path: str, n_pages: int = 1) -> None:
    import fitz
    doc = fitz.open()
    for _ in range(n_pages):
        doc.new_page()
    doc.save(path)
    doc.close()


# ── Model tests ───────────────────────────────────────────────────────────────

def test_workflow_node_roundtrip():
    node = WorkflowNode(node_type="source", node_id="abc123", params={"file_path": "/x.pdf"})
    d = node.to_dict()
    assert d["node_id"] == "abc123"
    restored = WorkflowNode.from_dict(d)
    assert restored.node_type == "source"
    assert restored.params["file_path"] == "/x.pdf"


def test_connection_roundtrip():
    conn = Connection("n1", "output", "n2", "input")
    d = conn.to_dict()
    restored = Connection.from_dict(d)
    assert restored.from_node == "n1"
    assert restored.to_port == "input"


def test_workflow_roundtrip():
    wf = _two_node_wf("/a.pdf")
    d = wf.to_dict()
    assert d["version"] == "1.0"
    wf2 = Workflow.from_dict(d)
    assert len(wf2.nodes) == 2
    assert len(wf2.connections) == 1
    assert wf2.connections[0].from_node == "n1"


def test_add_connection_replaces_duplicate_input():
    wf = Workflow()
    wf.add_node(WorkflowNode(node_type="source", node_id="a"))
    wf.add_node(WorkflowNode(node_type="source", node_id="b"))
    wf.add_node(WorkflowNode(node_type="sink",   node_id="c"))
    wf.add_connection(Connection("a", "output", "c", "input"))
    wf.add_connection(Connection("b", "output", "c", "input"))
    # Only one connection to c/input should remain
    to_c = [x for x in wf.connections if x.to_node == "c"]
    assert len(to_c) == 1
    assert to_c[0].from_node == "b"


def test_remove_node_cascades_connections():
    wf = _two_node_wf()
    wf.remove_node("n1")
    assert len(wf.nodes) == 1
    assert len(wf.connections) == 0


def test_get_node():
    wf = _two_node_wf()
    assert wf.get_node("n1").node_type == "source"
    assert wf.get_node("zzz") is None


# ── Serializer tests ──────────────────────────────────────────────────────────

def test_serializer_roundtrip(tmp_path):
    wf = _two_node_wf("/a.pdf")
    p = str(tmp_path / "test.wflow")
    serializer.save(wf, p)
    assert os.path.exists(p)
    wf2 = serializer.load(p)
    assert wf2.name == "Test WF"
    assert len(wf2.nodes) == 2


def test_serializer_is_valid_json(tmp_path):
    wf = _two_node_wf("/a.pdf")
    p = str(tmp_path / "test.json")
    serializer.save(wf, p)
    with open(p) as f:
        data = json.load(f)
    assert "nodes" in data
    assert "connections" in data


# ── Node registry tests ───────────────────────────────────────────────────────

def test_get_spec_known():
    spec = get_spec("source")
    assert spec is not None
    assert spec.title == "File Input"


def test_get_spec_unknown():
    assert get_spec("nonexistent_type_xyz") is None


def test_all_specs_nonempty():
    specs = all_specs()
    assert len(specs) > 5
    types = [s.node_type for s in specs]
    assert "source" in types
    assert "sink" in types


def test_specs_by_category():
    by_cat = specs_by_category()
    assert "I/O" in by_cat
    assert len(by_cat["I/O"]) >= 2


# ── Graph / topological sort tests ───────────────────────────────────────────

def test_topological_sort_simple():
    wf = _two_node_wf()
    order = topological_sort(wf)
    assert order.index("n1") < order.index("n2")


def test_topological_sort_detects_cycle():
    wf = Workflow()
    wf.add_node(WorkflowNode(node_type="source", node_id="a"))
    wf.add_node(WorkflowNode(node_type="sink",   node_id="b"))
    wf.connections.append(Connection("a", "output", "b", "input"))
    wf.connections.append(Connection("b", "output", "a", "input"))  # force cycle
    with pytest.raises(GraphError, match="cycle"):
        topological_sort(wf)


def test_topological_sort_chain():
    wf = Workflow()
    for nid in ("a", "b", "c"):
        wf.add_node(WorkflowNode(node_type="source", node_id=nid))
    wf.connections.append(Connection("a", "output", "b", "input"))
    wf.connections.append(Connection("b", "output", "c", "input"))
    order = topological_sort(wf)
    assert order == ["a", "b", "c"]


# ── Validate tests ────────────────────────────────────────────────────────────

def test_validate_ok():
    wf = _two_node_wf("/a.pdf")
    errors = validate(wf)
    assert errors == []


def test_validate_missing_connection_to_sink():
    wf = Workflow()
    snk = WorkflowNode(node_type="sink", node_id="s1")
    wf.add_node(snk)
    errors = validate(wf)
    assert any("input" in e for e in errors)


def test_validate_unknown_node_type():
    wf = Workflow()
    wf.add_node(WorkflowNode(node_type="ghost_tool_xyz", node_id="g1"))
    errors = validate(wf)
    assert any("ghost_tool_xyz" in e for e in errors)


def test_validate_dangling_connection():
    wf = _two_node_wf()
    wf.connections.append(Connection("ghost", "output", "n2", "input"))
    errors = validate(wf)
    assert any("ghost" in e for e in errors)


# ── Executor tests ────────────────────────────────────────────────────────────

def test_executor_source_to_sink(tmp_path):
    src = str(tmp_path / "in.pdf")
    _make_pdf(src)
    out = str(tmp_path / "out.pdf")
    wf = _two_node_wf(src, out)
    ex = WorkflowExecutor(wf, str(tmp_path))
    result = ex.execute()
    assert os.path.exists(out)


def test_executor_source_missing_file(tmp_path):
    wf = _two_node_wf("/nonexistent/file.pdf")
    ex = WorkflowExecutor(wf, str(tmp_path))
    with pytest.raises(GraphError, match="not found"):
        ex.execute()


def test_executor_cancel_flag(tmp_path):
    src = str(tmp_path / "in.pdf")
    _make_pdf(src)
    wf = _two_node_wf(src)
    cancel = [True]
    ex = WorkflowExecutor(wf, str(tmp_path), cancel_flag_ref=cancel)
    with pytest.raises(GraphError, match="Cancelled"):
        ex.execute()


def test_executor_raises_on_invalid_workflow(tmp_path):
    wf = Workflow()
    wf.add_node(WorkflowNode(node_type="sink", node_id="s"))
    ex = WorkflowExecutor(wf, str(tmp_path))
    with pytest.raises(GraphError, match="Validation failed"):
        ex.execute()


def test_executor_runs_a_real_tool_node(tmp_path):
    """source → watermark → sink. Guards the tool-node path, which
    source→sink alone never reaches."""
    from pdf_forge.tools.registry import registry
    registry.discover()

    src = str(tmp_path / "in.pdf")
    _make_pdf(src)
    out = str(tmp_path / "out.pdf")

    wf = Workflow(name="tool node")
    wf.add_node(WorkflowNode(node_type="source",    node_id="n1",
                             params={"file_path": src}))
    wf.add_node(WorkflowNode(node_type="watermark", node_id="n2",
                             params={"text": "DRAFT"}))
    wf.add_node(WorkflowNode(node_type="sink",      node_id="n3",
                             params={"output_path": out}))
    wf.add_connection(Connection("n1", "output", "n2", "input"))
    wf.add_connection(Connection("n2", "output", "n3", "input"))

    result = WorkflowExecutor(wf, str(tmp_path / "work")).execute()

    assert os.path.exists(out)
    # every node reports its outputs, sinks included
    assert result["n3"] == [out]


@pytest.mark.parametrize("node_type", [
    s.node_type for s in all_specs() if s.node_type not in ("source", "sink")
])
def test_node_params_match_tool_create_job(node_type):
    """Every node's declared params must satisfy its tool's create_job()."""
    from pdf_forge.tools.registry import registry
    registry.discover()

    spec = get_spec(node_type)
    tool = registry.get(node_type)
    assert tool is not None, f"{node_type} has a node spec but no registered tool"

    # mirror WorkflowExecutor._run_node's param construction
    params = dict(spec.param_defs)
    if spec.inputs:
        port = spec.inputs[0]
        params["input_paths" if port.multiple else "input_path"] = ["in.pdf"] if port.multiple else "in.pdf"
    if spec.outputs:
        port = spec.outputs[0]
        if port.data_type in ("image", "pdf_dir"):
            params["output_dir"] = str(tempfile.gettempdir())
        elif port.data_type in ("text", "excel"):
            params["output_path"] = "out.txt"
        else:
            params.setdefault("output_path", "out.pdf")

    tool.create_job(params)  # must not raise
