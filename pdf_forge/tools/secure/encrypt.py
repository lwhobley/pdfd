"""Encrypt and Decrypt PDF tools."""
from __future__ import annotations
from typing import Any

import pikepdf

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class EncryptJob(Job):
    """Encrypt a PDF with user and owner passwords.

    R=6 = AES-256 (PDF 2.0), R=4 = AES-128 (PDF 1.6)
    permissions: dict of boolean flags matching pikepdf.Permissions
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        user_password: str,
        owner_password: str,
        encryption_r: int = 6,
        allow_printing: bool = True,
        allow_modification: bool = False,
        allow_copy: bool = True,
        allow_annotations: bool = False,
    ) -> None:
        super().__init__("encrypt_pdf", [input_path])
        self.output_path = output_path
        self.user_password = user_password
        self.owner_password = owner_password
        self.encryption_r = encryption_r
        self.allow_printing = allow_printing
        self.allow_modification = allow_modification
        self.allow_copy = allow_copy
        self.allow_annotations = allow_annotations

    def execute(self) -> JobResult:
        self.log(f"Encrypting with AES-{'256' if self.encryption_r == 6 else '128'}")
        permissions = pikepdf.Permissions(
            print_lowres=self.allow_printing,
            print_highres=self.allow_printing,
            modify_other=self.allow_modification,
            extract=self.allow_copy,
            modify_annotation=self.allow_annotations,
        )
        encryption = pikepdf.Encryption(
            owner=self.owner_password or "",
            user=self.user_password,
            R=self.encryption_r,
            allow=permissions,
        )
        with pikepdf.open(self.input_paths[0]) as pdf:
            pdf.save(self.output_path, encryption=encryption)
        self.report_progress(100)
        self.log("Encryption applied")
        return JobResult(output_paths=[self.output_path])


class DecryptJob(Job):
    """Remove encryption from a PDF (requires the owner or user password)."""

    def __init__(
        self,
        input_path: str,
        output_path: str,
        password: str,
    ) -> None:
        super().__init__("decrypt_pdf", [input_path])
        self.output_path = output_path
        self.password = password

    def execute(self) -> JobResult:
        self.log("Decrypting PDF")
        try:
            with pikepdf.open(self.input_paths[0], password=self.password) as pdf:
                pdf.save(self.output_path)
        except pikepdf.PasswordError as e:
            raise Exception(f"Wrong password: {e}") from e
        self.report_progress(100)
        self.log("Decryption complete")
        return JobResult(output_paths=[self.output_path])


class EncryptTool(BaseTool):
    meta = ToolMeta(
        tool_id="encrypt_pdf",
        name="Encrypt PDF",
        description="Protect a PDF with AES-256 user/owner passwords and permissions.",
        category="secure",
        icon="encrypt",
    )

    def create_job(self, params: dict[str, Any]) -> EncryptJob:
        return EncryptJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            user_password=params.get("user_password", ""),
            owner_password=params.get("owner_password", ""),
            encryption_r=params.get("encryption_r", 6),
            allow_printing=params.get("allow_printing", True),
            allow_modification=params.get("allow_modification", False),
            allow_copy=params.get("allow_copy", True),
            allow_annotations=params.get("allow_annotations", False),
        )


class DecryptTool(BaseTool):
    meta = ToolMeta(
        tool_id="decrypt_pdf",
        name="Decrypt PDF",
        description="Remove password protection from a PDF (requires the correct password).",
        category="secure",
        icon="decrypt",
    )

    def create_job(self, params: dict[str, Any]) -> DecryptJob:
        return DecryptJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            password=params.get("password", ""),
        )
