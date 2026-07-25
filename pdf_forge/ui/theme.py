"""App theme — dark/light QSS applied to QApplication."""
from __future__ import annotations
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
}
QMenuBar::item:selected {
    background-color: #313244;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QMenu::item:selected {
    background-color: #45475a;
}

QToolBar {
    background-color: #181825;
    border: none;
    spacing: 4px;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}

QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background: #181825;
    color: #a6adc8;
    padding: 6px 14px;
    border: 1px solid #313244;
    border-bottom: none;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1e1e2e;
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover {
    background: #313244;
}

QScrollArea, QScrollBar {
    background-color: #181825;
}
QScrollBar:vertical {
    width: 10px;
    background: #1e1e2e;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    height: 10px;
    background: #1e1e2e;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 4px;
    min-width: 20px;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px 12px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:default {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
}
QPushButton:default:hover {
    background-color: #b4befe;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 6px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #89b4fa;
}

QListWidget, QTreeWidget, QListView, QTreeView {
    background-color: #181825;
    color: #cdd6f4;
    border: none;
    outline: none;
}
QListWidget::item:selected, QListView::item:selected {
    background-color: #313244;
    color: #cdd6f4;
}
QListWidget::item:hover, QListView::item:hover {
    background-color: #26273a;
}

QSplitter::handle {
    background-color: #313244;
    width: 2px;
    height: 2px;
}

QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 3px;
}

QGroupBox {
    color: #a6adc8;
    border: 1px solid #313244;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}

QLabel {
    color: #cdd6f4;
    background: transparent;
}

QCheckBox {
    color: #cdd6f4;
    spacing: 6px;
}

QDockWidget {
    titlebar-close-icon: none;
    color: #cdd6f4;
}
QDockWidget::title {
    background: #181825;
    padding: 4px 8px;
    border-bottom: 1px solid #313244;
}
"""


LIGHT_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #e6e9ef;
    color: #4c4f69;
}
QTabBar::tab {
    background: #e6e9ef;
    color: #6c6f85;
    padding: 6px 14px;
}
QTabBar::tab:selected {
    background: #eff1f5;
    color: #4c4f69;
    border-bottom: 2px solid #1e66f5;
}
QPushButton {
    background-color: #dce0e8;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    border-radius: 4px;
    padding: 5px 12px;
}
QPushButton:default {
    background-color: #1e66f5;
    color: #eff1f5;
    border: none;
}
"""


def apply_theme(app: QApplication, theme: str = "dark") -> None:
    qss = DARK_QSS if theme == "dark" else LIGHT_QSS
    app.setStyleSheet(qss)
