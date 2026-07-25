"""Workflow editor window — palette + canvas + toolbar + properties panel."""
from __future__ import annotations
import os
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox, QLabel, QStatusBar,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QInputDialog,
)
from PySide6.QtCore import Qt, QSize, Slot
from PySide6.QtGui import QAction, QKeySequence

from pdf_forge.workflow.model import Workflow, WorkflowNode
from pdf_forge.workflow.node_registry import get_spec
from pdf_forge.workflow import serializer
from pdf_forge.ui.workflow.canvas import WorkflowScene, WorkflowView
from pdf_forge.ui.workflow.palette import NodePalette

log = logging.getLogger(__name__)


class WorkflowWindow(QMainWindow):
    """Standalone window for the visual workflow editor."""

    def __init__(self, workflow: Workflow | None = None, parent=None) -> None:
        super().__init__(parent)
        self._workflow = workflow or Workflow()
        self._file_path: str | None = None
        self.setWindowTitle(f"Workflow Editor — {self._workflow.name}")
        self.resize(1100, 700)

        self._build_ui()
        self._build_toolbar()
        self._build_menu()
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Drag nodes from the palette onto the canvas.")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # Left palette
        self._palette = NodePalette()
        splitter.addWidget(self._palette)

        # Canvas
        self._scene = WorkflowScene(self._workflow)
        self._scene.workflow_changed.connect(self._on_changed)
        self._scene.node_edit_requested.connect(self._edit_node)
        self._view = WorkflowView(self._scene)
        self._view.setAcceptDrops(True)
        splitter.addWidget(self._view)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([190, 880])
        layout.addWidget(splitter)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Workflow Toolbar")
        tb.setIconSize(QSize(18, 18))
        tb.setMovable(False)
        self.addToolBar(tb)

        act_run = QAction("▶  Run", self)
        act_run.setShortcut(QKeySequence("F5"))
        act_run.setToolTip("Execute the workflow (F5)")
        act_run.triggered.connect(self._run_workflow)
        tb.addAction(act_run)

        tb.addSeparator()

        act_fit = QAction("Fit", self)
        act_fit.triggered.connect(self._view.zoom_fit)
        tb.addAction(act_fit)

        act_reset = QAction("100%", self)
        act_reset.triggered.connect(self._view.zoom_reset)
        tb.addAction(act_reset)

        tb.addSeparator()

        act_del = QAction("Delete", self)
        act_del.setShortcut(QKeySequence.Delete)
        act_del.triggered.connect(self._scene.delete_selected)
        tb.addAction(act_del)

        tb.addSeparator()

        self._lbl_status = QLabel("  Ready")
        tb.addWidget(self._lbl_status)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        act_new = file_menu.addAction("New Workflow")
        act_new.setShortcut(QKeySequence.New)
        act_new.triggered.connect(self._new_workflow)

        act_open = file_menu.addAction("Open…")
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._open_workflow)

        act_save = file_menu.addAction("Save")
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self._save_workflow)

        act_save_as = file_menu.addAction("Save As…")
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._save_as)

        edit_menu = mb.addMenu("&Edit")
        act_del = edit_menu.addAction("Delete Selected")
        act_del.setShortcut(QKeySequence.Delete)
        act_del.triggered.connect(self._scene.delete_selected)

        act_sel_all = edit_menu.addAction("Select All")
        act_sel_all.setShortcut(QKeySequence.SelectAll)
        act_sel_all.triggered.connect(lambda: [
            i.setSelected(True) for i in self._scene.items()
        ])

        run_menu = mb.addMenu("&Run")
        act_run = run_menu.addAction("Execute Workflow")
        act_run.setShortcut(QKeySequence("F5"))
        act_run.triggered.connect(self._run_workflow)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_changed(self) -> None:
        title = f"Workflow Editor — {self._workflow.name} *"
        self.setWindowTitle(title)

    def _new_workflow(self) -> None:
        self._workflow = Workflow()
        self._file_path = None
        self._scene._workflow = self._workflow
        self._scene._load_workflow()
        self.setWindowTitle("Workflow Editor — Untitled *")

    def _open_workflow(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Workflow", "",
            "Workflow Files (*.wflow *.json);;All Files (*)"
        )
        if not path:
            return
        try:
            self._workflow = serializer.load(path)
            self._file_path = path
            self._scene._workflow = self._workflow
            self._scene._load_workflow()
            self.setWindowTitle(f"Workflow Editor — {self._workflow.name}")
        except Exception as e:
            QMessageBox.critical(self, "Open Failed", str(e))

    def _save_workflow(self) -> None:
        if self._file_path:
            self._do_save(self._file_path)
        else:
            self._save_as()

    def _save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Workflow", f"{self._workflow.name}.wflow",
            "Workflow Files (*.wflow);;JSON (*.json)"
        )
        if path:
            self._file_path = path
            self._do_save(path)

    def _do_save(self, path: str) -> None:
        try:
            serializer.save(self._workflow, path)
            self.setWindowTitle(f"Workflow Editor — {self._workflow.name}")
            self._status.showMessage(f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))

    @Slot(str)
    def _edit_node(self, node_id: str) -> None:
        node = self._workflow.get_node(node_id)
        if not node:
            return
        spec = get_spec(node.node_type)
        if not spec:
            return

        # Source node — show file picker
        if node.node_type == "source":
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Input File", node.params.get("file_path", ""),
                "PDF Files (*.pdf);;All Files (*)"
            )
            if path:
                node.params["file_path"] = path
                self._status.showMessage(f"Source → {os.path.basename(path)}")
            return

        # Sink node — show save path picker
        if node.node_type == "sink":
            path, _ = QFileDialog.getSaveFileName(
                self, "Select Output File", node.params.get("output_path", ""),
                "PDF Files (*.pdf);;All Files (*)"
            )
            if path:
                node.params["output_path"] = path
                self._status.showMessage(f"Sink → {os.path.basename(path)}")
            return

        # Generic param editor
        dlg = _NodeParamDialog(node, spec, parent=self)
        dlg.exec()

    def _run_workflow(self) -> None:
        from pdf_forge.workflow.graph import validate, WorkflowExecutor, GraphError
        from pdf_forge.workers.job_queue import JobQueue

        errors = validate(self._workflow)
        if errors:
            QMessageBox.warning(
                self, "Workflow Invalid",
                "Cannot run — please fix these issues:\n\n"
                + "\n".join(f"• {e}" for e in errors)
            )
            return

        out_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Folder for Workflow Results"
        )
        if not out_dir:
            return

        self._lbl_status.setText("  Running…")

        def on_progress(node_id: str, pct: int) -> None:
            self._status.showMessage(f"[{node_id}] {pct}%")

        def on_log(node_id: str, msg: str) -> None:
            log.info("[%s] %s", node_id, msg)

        from PySide6.QtCore import QThread

        class _RunThread(QThread):
            def __init__(self, wf, out_dir, progress_cb, log_cb):
                super().__init__()
                self._wf = wf
                self._out = out_dir
                self._pcb = progress_cb
                self._lcb = log_cb
                self.result = {}
                self.error = ""

            def run(self):
                try:
                    ex = WorkflowExecutor(
                        self._wf, self._out,
                        progress_cb=self._pcb,
                        log_cb=self._lcb,
                    )
                    self.result = ex.execute()
                except Exception as e:
                    self.error = str(e)

        self._run_thread = _RunThread(
            self._workflow, out_dir, on_progress, on_log
        )
        self._run_thread.finished.connect(self._on_run_finished)
        self._run_thread.start()

    def _on_run_finished(self) -> None:
        thread = self._run_thread
        if thread.error:
            QMessageBox.critical(self, "Workflow Failed", thread.error)
            self._lbl_status.setText("  Failed")
        else:
            n = sum(len(v) for v in thread.result.values())
            self._lbl_status.setText(f"  Done ({n} output(s))")
            self._status.showMessage(
                f"Workflow complete — {n} output file(s) written."
            )

    def closeEvent(self, event) -> None:
        # Qt aborts the process if a running QThread is destroyed
        thread = getattr(self, "_run_thread", None)
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            if not thread.wait(5000):
                log.warning("Workflow thread did not stop in time; terminating")
                thread.terminate()
                thread.wait()
        super().closeEvent(event)


# ── Generic param editor ──────────────────────────────────────────────────────

class _NodeParamDialog(QDialog):
    def __init__(self, node: WorkflowNode, spec, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit: {spec.title}")
        self._node = node
        self._fields: dict[str, QLineEdit] = {}
        self._build_ui(spec)

    def _build_ui(self, spec) -> None:
        vbox = QVBoxLayout(self)
        form = QFormLayout()

        for key, default in (spec.param_defs or {}).items():
            val = self._node.params.get(key, default)
            edit = QLineEdit(str(val) if val is not None else "")
            edit.setPlaceholderText(str(default) if default is not None else "")
            self._fields[key] = edit
            form.addRow(key + ":", edit)

        vbox.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        vbox.addWidget(btns)

    def _accept(self) -> None:
        for key, edit in self._fields.items():
            raw = edit.text()
            # Try to parse booleans and numbers
            if raw.lower() == "true":
                self._node.params[key] = True
            elif raw.lower() == "false":
                self._node.params[key] = False
            else:
                try:
                    self._node.params[key] = int(raw)
                except ValueError:
                    try:
                        self._node.params[key] = float(raw)
                    except ValueError:
                        self._node.params[key] = raw
        self.accept()
