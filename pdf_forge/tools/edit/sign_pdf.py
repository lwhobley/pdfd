"""Digital signature tool using pyhanko.

Signs a PDF with a PFX/P12 certificate.
Produces a visible signature appearance with name, date, reason, location.

Requires: pyhanko, pyhanko-certvalidator
"""
from __future__ import annotations
import os
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class SignPDFJob(Job):
    """Apply a digital signature to a PDF page.

    pfx_path     — path to .pfx / .p12 certificate file
    pfx_password — password for the PFX file
    page         — 0-indexed page to place the signature (default last)
    rect         — (x0, y0, x1, y1) in PDF units for the visible sig box
    reason       — signature reason string
    location     — signer's location string
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        pfx_path: str,
        pfx_password: str = "",
        page: int = -1,
        rect: tuple[float, float, float, float] = (50, 50, 250, 100),
        reason: str = "",
        location: str = "",
        contact_info: str = "",
        name: str = "",
    ) -> None:
        super().__init__("sign_pdf", [input_path])
        self.output_path = output_path
        self.pfx_path = pfx_path
        self.pfx_password = pfx_password
        self.page = page
        self.rect = rect
        self.reason = reason
        self.location = location
        self.contact_info = contact_info
        self.name = name

    def execute(self) -> JobResult:
        try:
            from pyhanko.sign import signers, fields
            from pyhanko.sign.fields import SigSeedSubFilter
            from pyhanko.pdf_utils.reader import PdfFileReader
            from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
            from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
        except ImportError:
            raise RuntimeError(
                "pyhanko is required for digital signatures. "
                "Run: pip install pyhanko pyhanko-certvalidator"
            )

        self.log(f"Loading certificate: {os.path.basename(self.pfx_path)}")

        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=self.pfx_path,
            passphrase=self.pfx_password.encode() if self.pfx_password else b"",
        )

        with open(self.input_paths[0], "rb") as inf:
            reader = PdfFileReader(inf, strict=False)
            w = IncrementalPdfFileWriter(inf)

            page_num = self.page if self.page >= 0 else reader.get_num_pages() - 1
            x0, y0, x1, y1 = self.rect

            # Add a visible signature field
            field_name = "Sig1"
            sig_field_spec = fields.SigFieldSpec(
                sig_field_name=field_name,
                on_page=page_num,
                box=(x0, y0, x1, y1),
            )
            fields.append_signature_field(w, sig_field_spec)

            meta = PdfSignatureMetadata(
                field_name=field_name,
                reason=self.reason or None,
                location=self.location or None,
                contact_info=self.contact_info or None,
                name=self.name or None,
            )

            self.log("Applying signature…")
            with open(self.output_path, "wb") as outf:
                signers.sign_pdf(
                    w,
                    signature_meta=meta,
                    signer=signer,
                    output=outf,
                )

        self.report_progress(100)
        self.log("Signature applied")
        return JobResult(output_paths=[self.output_path])


class SignPDFTool(BaseTool):
    meta = ToolMeta(
        tool_id="sign_pdf",
        name="Sign PDF",
        description="Apply an X.509 digital signature using a PFX/P12 certificate.",
        category="edit",
        icon="sign",
        requires=[],
    )

    def create_job(self, params: dict[str, Any]) -> SignPDFJob:
        return SignPDFJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            pfx_path=params["pfx_path"],
            pfx_password=params.get("pfx_password", ""),
            page=params.get("page", -1),
            rect=tuple(params.get("rect", (50, 50, 250, 100))),
            reason=params.get("reason", ""),
            location=params.get("location", ""),
            contact_info=params.get("contact_info", ""),
            name=params.get("name", ""),
        )
