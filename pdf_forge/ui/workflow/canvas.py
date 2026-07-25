"""Workflow canvas — QGraphicsScene + QGraphicsView."""
from __future__ import annotations
import logging

from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem,
)
from PySide6.QtCore import Qt, QPointF, Signal, QObject
from PySide6.QtGui import QColor, QPainter, QWheelEvent, QKeyEvent, QTransform

from pdf_forge.workflow.model import Workflow, WorkflowNode, Connection
from pdf_forge.workflow.node_registry import get_spec
from pdf_forge.ui.workflow.items import NodeItem, EdgeItem, PortItem, TempEdgeItem

log = logging.getLogger(__name__)


class WorkflowScene(QGraphicsScene):
    """Scene that owns the workflow model and all graphics items."""

    node_edit_requested = Signal(str)          # node_id
    workflow_changed    = Signal()             # any structural change

    def __init__(self, workflow: Workflow, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workflow = workflow
        self._node_items:  dict[str, NodeItem] = {}   # node_id → item
        self._edge_items:  list[EdgeItem] = []
        self._drag_port:   PortItem | None = None
        self._temp_edge:   TempEdgeItem | None = None

        self.setBackgroundBrush(QColor("#1e1e2e"))
        self._load_workflow()

    @property
    def workflow(self) -> Workflow:
        return self._workflow

    # ── Load / rebuild ────────────────────────────────────────────────────────

    def _load_workflow(self) -> None:
        self.clear()
        self._node_items.clear()
        self._edge_items.clear()

        for node in self._workflow.nodes:
            self._add_node_item(node)

        for conn in self._workflow.connections:
            self._add_edge_item(conn)

    def _add_node_item(self, wf_node: WorkflowNode) -> NodeItem:
        spec = get_spec(wf_node.node_type)
        if not spec:
            return None
        item = NodeItem(wf_node, spec)
        self.addItem(item)
        self._node_items[wf_node.node_id] = item
        return item

    def _add_edge_item(self, conn: Connection) -> EdgeItem | None:
        from_item = self._node_items.get(conn.from_node)
        to_item   = self._node_items.get(conn.to_node)
        if not from_item or not to_item:
            return None
        from_port = from_item.get_port(conn.from_port, is_output=True)
        to_port   = to_item.get_port(conn.to_port,   is_output=False)
        if not from_port or not to_port:
            return None
        edge = EdgeItem(from_port, to_port)
        self.addItem(edge)
        self._edge_items.append(edge)
        return edge

    # ── Public API ────────────────────────────────────────────────────────────

    def add_node(self, node_type: str, pos: QPointF) -> WorkflowNode | None:
        spec = get_spec(node_type)
        if not spec:
            return None
        wf_node = WorkflowNode(
            node_type=node_type,
            position=(pos.x(), pos.y()),
            params=dict(spec.param_defs),
        )
        self._workflow.add_node(wf_node)
        self._add_node_item(wf_node)
        self.workflow_changed.emit()
        return wf_node

    def delete_selected(self) -> None:
        for item in list(self.selectedItems()):
            if isinstance(item, NodeItem):
                self._remove_node(item)
            elif isinstance(item, EdgeItem):
                self._remove_edge(item)
        self.workflow_changed.emit()

    def _remove_node(self, item: NodeItem) -> None:
        node_id = item.wf_node.node_id
        # Remove all edges connected to this node
        for edge in [e for e in self._edge_items
                     if e.from_port.node_item is item or e.to_port.node_item is item]:
            self._edge_items.remove(edge)
            self.removeItem(edge)
        self._workflow.remove_node(node_id)
        del self._node_items[node_id]
        self.removeItem(item)

    def _remove_edge(self, edge: EdgeItem) -> None:
        fp = edge.from_port
        tp = edge.to_port
        self._workflow.remove_connection(
            fp.node_item.wf_node.node_id, fp.port_name,
            tp.node_item.wf_node.node_id, tp.port_name,
        )
        self._edge_items.remove(edge)
        self.removeItem(edge)

    # ── Connection drag ───────────────────────────────────────────────────────

    def start_connection(self, port: PortItem) -> None:
        self._drag_port = port
        start = port.scene_center()
        self._temp_edge = TempEdgeItem(start)
        self.addItem(self._temp_edge)

    def mouseMoveEvent(self, event) -> None:
        if self._temp_edge:
            self._temp_edge.update_end(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_port and self._temp_edge:
            self.removeItem(self._temp_edge)
            self._temp_edge = None

            target = self._port_at(event.scenePos())
            if target and self._can_connect(self._drag_port, target):
                self._finish_connection(self._drag_port, target)

            self._drag_port = None
        super().mouseReleaseEvent(event)

    def _port_at(self, pos: QPointF) -> PortItem | None:
        for item in self.items(pos):
            if isinstance(item, PortItem):
                return item
        return None

    def _can_connect(self, a: PortItem, b: PortItem) -> bool:
        if a is b:
            return False
        if a.is_output == b.is_output:
            return False
        if a.node_item is b.node_item:
            return False
        return True

    def _finish_connection(self, a: PortItem, b: PortItem) -> None:
        out_port = a if a.is_output else b
        in_port  = b if b.is_output else a
        conn = Connection(
            from_node=out_port.node_item.wf_node.node_id,
            from_port=out_port.port_name,
            to_node=in_port.node_item.wf_node.node_id,
            to_port=in_port.port_name,
        )
        self._workflow.add_connection(conn)
        edge = EdgeItem(out_port, in_port)
        self.addItem(edge)
        self._edge_items.append(edge)
        self.workflow_changed.emit()

    # ── Edge update (on node move) ────────────────────────────────────────────

    def update_edges_for_node(self, node_item: NodeItem) -> None:
        for edge in self._edge_items:
            if (edge.from_port.node_item is node_item
                    or edge.to_port.node_item is node_item):
                edge.update_path()

    # ── Edit signal ───────────────────────────────────────────────────────────

    def request_node_edit(self, node_id: str) -> None:
        self.node_edit_requested.emit(node_id)

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        elif event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
            for item in self.items():
                if isinstance(item, NodeItem):
                    item.setSelected(True)
        else:
            super().keyPressEvent(event)


class WorkflowView(QGraphicsView):
    """Scrollable, zoomable view of the WorkflowScene."""

    def __init__(self, scene: WorkflowScene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(self.NoFrame)
        self._zoom = 1.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_zoom = self._zoom * factor
        if 0.2 <= new_zoom <= 4.0:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def zoom_reset(self) -> None:
        self.setTransform(QTransform())
        self._zoom = 1.0

    def zoom_fit(self) -> None:
        self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        node_type = event.mimeData().text()
        pos = self.mapToScene(event.position().toPoint())
        scene: WorkflowScene = self.scene()
        scene.add_node(node_type, pos)
        event.acceptProposedAction()
