"""Application bootstrap: QApplication setup, theme, and main window launch."""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon

from pdf_forge import APP_NAME, ORG_NAME, __version__
from pdf_forge.core.logging_config import setup_logging
from pdf_forge.persistence.settings import AppSettings
from pdf_forge.ui.theme import apply_theme
from pdf_forge.ui.main_window import MainWindow


def run() -> int:
    setup_logging()

    # High-DPI
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationVersion(__version__)

    # App icon — works both in dev and frozen (PyInstaller) mode
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)) + "/..")
    icon_path = os.path.join(base, "pdf_forge", "assets", "icons", "app.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    settings = AppSettings()
    apply_theme(app, settings.theme)

    window = MainWindow(settings)
    window.show()

    # Open files passed on command line
    for arg in sys.argv[1:]:
        if os.path.isfile(arg) and arg.lower().endswith(".pdf"):
            window.open_file(arg)

    return app.exec()
