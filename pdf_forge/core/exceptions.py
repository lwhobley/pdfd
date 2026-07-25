"""Application-level exceptions."""


class PDFForgeError(Exception):
    """Base exception for all app errors."""


class PDFOpenError(PDFForgeError):
    """Cannot open or parse a PDF file."""


class PDFSaveError(PDFForgeError):
    """Cannot save a PDF file."""


class ToolError(PDFForgeError):
    """A tool job failed."""


class JobCancelledError(PDFForgeError):
    """Job was cancelled by the user."""


class CapabilityMissingError(PDFForgeError):
    """Required external tool or library is not available."""

    def __init__(self, capability: str, hint: str = ""):
        self.capability = capability
        self.hint = hint
        msg = f"Required capability '{capability}' is not available."
        if hint:
            msg += f" {hint}"
        super().__init__(msg)
