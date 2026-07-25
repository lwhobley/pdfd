"""Qt graphics items: NodeItem, PortItem, EdgeItem."""
from __future__ import annotations
import math
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsRectItem, QStyleOptionGraphicsItem, QWidget,
    QGraphicsTextItem,
)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QPainter, QPainterPath, QFont,
)

if TYPE_CHECKING:
    from pdf_forge.workflow.model import NodeSpec, WorkflowNode


# ── Colors ────────────────────────────────────────────────────────────────────

_PORT_COLORS = {
    "pdf":      QColor("#5b9bd5"),
    "pdf_list": QColor("#5b9bd5"),
    "image":    QColor("#70c97e"),
    "text":     QColor("#f5c842"),
    "excel":    QColor("#a8d87a"),
    "any":      QColor("#aaaaaa"),
}

_NODE_TITLE_H = 28
_NODE_WIDTH   = 200
_PORT_R       = 7
_PORT_GAP     = 22


def port_color(data_type: str) -> QColor:
    return _PORT_COLORS.get(data_type, _PORT_COLORS["any"])


# ── PortItem ──────────────────────────────────────────────────────────────────

class PortItem(QGraphicsEllipseItem):
    """A single input or output port circle on a NodeItem."""

    def __init__(
        self,
        node_item: "NodeItem",
        port_name: str,
        data_type: str,
        is_output: bool,
        index: int,
        parent: QGraphicsItem,
    ) -> None:
        r = _PORT_R
        super().__init__(-r, -r, r * 2, r * 2, parent)
        self.node_item  = node_item
        self.port_name  = port_name
        self.data_type  = data_type
        self.is_output  = is_output
        self.index      = index

        color = port_color(data_type)
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(140), 1.5))
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(2)

    def scene_center(self) -> QPointF:
        return self.mapToScene(QPointF(0, 0))

    def hoverEnterEvent(self, event) -> None:
        self.setBrush(QBrush(port_color(self.data_type).lighter(150)))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setBrush(QBrush(port_color(self.data_type)))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            scene = self.scene()
            if hasattr(scene, "start_connection"):
                scene.start_connection(self)
        event.accept()


# ── NodeItem ──────────────────────────────────────────────────────────────────

class NodeItem(QGraphicsItem):
    """A single workflow node on the canvas."""

    def __init__(
        self,
        wf_node: "WorkflowNode",
        spec: "NodeSpec",
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.wf_node = wf_node
        self.spec    = spec

        self._base_color  = QColor(spec.color)
        self._title_color = self._base_color.lighter(140)

        n_ports = max(len(spec.inputs), len(spec.outputs))
        body_h = max(n_ports * _PORT_GAP + 16, 40)
        self._width  = _NODE_WIDTH
        self._height = _NODE_TITLE_H + body_h

        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsScenePositionChanges
        )
        self.setZValue(1)
        self.setPos(*wf_node.position)

        self._in_ports:  list[PortItem] = []
        self._out_ports: list[PortItem] = []
        self._build_ports()

    def _build_ports(self) -> None:
        body_h = self._height - _NODE_TITLE_H
        for i, port_spec in enumerate(self.spec.inputs):
            y = _NODE_TITLE_H + body_h / (len(self.spec.inputs) + 1) * (i + 1)
            p = PortItem(self, port_spec.name, port_spec.data_type, False, i, self)
            p.setPos(0, y)
            self._in_ports.append(p)

        for i, port_spec in enumerate(self.spec.outputs):
            y = _NODE_TITLE_H + body_h / (len(self.spec.outputs) + 1) * (i + 1)
            p = PortItem(self, port_spec.name, port_spec.data_type, True, i, self)
            p.setPos(self._width, y)
            self._out_ports.append(p)

    def get_port(self, name: str, is_output: bool) -> PortItem | None:
        ports = self._out_ports if is_output else self._in_ports
        return next((p for p in ports if p.port_name == name), None)

    def boundingRect(self) -> QRectF:
        return QRectF(-2, -2, self._width + 4, self._height + 4)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        selected = self.isSelected()
        w, h = self._width, self._height

        # Shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(4, 4, w, h, 6, 6)

        # Body
        painter.setBrush(QBrush(self._base_color))
        pen = QPen(QColor("#89b4fa") if selected else QColor("#45475a"), 2 if selected else 1)
        painter.setPen(pen)
        painter.drawRoundedRect(0, 0, w, h, 6, 6)

        # Title bar
        title_rect = QRectF(0, 0, w, _NODE_TITLE_H)
        painter.setBrush(QBrush(self._title_color))
        painter.setPen(Qt.NoPen)
        # Clip to round top corners
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, _NODE_TITLE_H + 6, 6, 6)
        path.addRect(0, 6, w, _NODE_TITLE_H)
        painter.drawPath(path)

        # Title text
        painter.setPen(QColor("#cdd6f4"))
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        title = self.wf_node.label or self.spec.title
        painter.drawText(QRectF(10, 0, w - 20, _NODE_TITLE_H), Qt.AlignVCenter, title)

        # Port labels
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#a6adc8"))

        body_h = self._height - _NODE_TITLE_H
        for i, port_spec in enumerate(self.spec.inputs):
            y = _NODE_TITLE_H + body_h / (len(self.spec.inputs) + 1) * (i + 1)
            painter.drawText(
                QRectF(14, y - 8, w / 2 - 14, 16),
                Qt.AlignVCenter,
                port_spec.display(),
            )
        for i, port_spec in enumerate(self.spec.outputs):
            y = _NODE_TITLE_H + body_h / (len(self.spec.outputs) + 1) * (i + 1)
            painter.drawText(
                QRectF(w / 2, y - 8, w / 2 - 14, 16),
                Qt.AlignVCenter | Qt.AlignRight,
                port_spec.display(),
            )

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.wf_node.position = (self.pos().x(), self.pos().y())
            scene = self.scene()
            if hasattr(scene, "update_edges_for_node"):
                scene.update_edges_for_node(self)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event) -> None:
        scene = self.scene()
        if hasattr(scene, "request_node_edit"):
            scene.request_node_edit(self.wf_node.node_id)
        event.accept()


# ── EdgeItem ──────────────────────────────────────────────────────────────────

class EdgeItem(QGraphicsPathItem):
    """Bezier curve connecting an output port to an input port."""

    def __init__(
        self,
        from_port: PortItem,
        to_port: PortItem,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.from_port = from_port
        self.to_port   = to_port
        self.setZValue(0)
        color = port_color(from_port.data_type)
        self.setPen(QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.update_path()

    def update_path(self) -> None:
        p1 = self.from_port.scene_center()
        p2 = self.to_port.scene_center()
        self._set_bezier(p1, p2)

    def set_end(self, end: QPointF) -> None:
        p1 = self.from_port.scene_center()
        self._set_bezier(p1, end)

    def _set_bezier(self, p1: QPointF, p2: QPointF) -> None:
        dx = abs(p2.x() - p1.x()) * 0.5
        path = QPainterPath(p1)
        path.cubicTo(
            QPointF(p1.x() + dx, p1.y()),
            QPointF(p2.x() - dx, p2.y()),
            p2,
        )
        self.setPath(path)

    def shape(self) -> QPainterPath:
        # Wider shape for easier selection
        stroker = self.path()
        return stroker


# ── Temporary drag-edge ───────────────────────────────────────────────────────

class TempEdgeItem(QGraphicsPathItem):
    """Dashed bezier drawn while the user is dragging a new connection."""

    def __init__(self, start: QPointF) -> None:
        super().__init__()
        self._start = start
        pen = QPen(QColor("#cdd6f4"), 1.5, Qt.DashLine)
        self.setPen(pen)
        self.setZValue(10)
        self.update_end(start)

    def update_end(self, end: QPointF) -> None:
        dx = abs(end.x() - self._start.x()) * 0.5
        path = QPainterPath(self._start)
        path.cubicTo(
            QPointF(self._start.x() + dx, self._start.y()),
            QPointF(end.x() - dx, end.y()),
            end,
        )
        self.setPath(path)
