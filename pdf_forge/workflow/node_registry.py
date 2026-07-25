"""Maps tool_id → NodeSpec describing ports and default params."""
from __future__ import annotations
from pdf_forge.workflow.model import NodeSpec, PortSpec

_pdf_in  = PortSpec("input",  "pdf",  "PDF In")
_pdf_out = PortSpec("output", "pdf",  "PDF Out")
_pdfs_in = PortSpec("inputs", "pdf",  "PDFs In", multiple=True)

_SPECS: list[NodeSpec] = [
    # ── Source / Sink ─────────────────────────────────────────────────────
    NodeSpec(
        node_type="source",
        title="File Input",
        category="I/O",
        inputs=[],
        outputs=[PortSpec("output", "pdf", "PDF Out")],
        param_defs={"file_path": ""},
        color="#1e6b6b",
    ),
    NodeSpec(
        node_type="sink",
        title="File Output",
        category="I/O",
        inputs=[_pdf_in],
        outputs=[],
        param_defs={"output_path": ""},
        color="#6b1e1e",
    ),

    # ── Organize ──────────────────────────────────────────────────────────
    NodeSpec(
        node_type="merge_pdfs",
        title="Merge PDFs",
        category="Organize",
        inputs=[_pdfs_in],
        outputs=[_pdf_out],
        param_defs={},
        color="#313244",
    ),
    NodeSpec(
        node_type="split_pdf",
        title="Split PDF",
        category="Organize",
        inputs=[_pdf_in],
        outputs=[PortSpec("outputs", "pdf_dir", "Parts Out", multiple=True)],
        param_defs={"mode": "every_n", "every_n": 1, "ranges": ""},
        color="#313244",
    ),
    NodeSpec(
        node_type="rotate_pages",
        title="Rotate Pages",
        category="Organize",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"degrees": 90, "page_indices": []},
        color="#313244",
    ),
    NodeSpec(
        node_type="reverse_pages",
        title="Reverse Pages",
        category="Organize",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        color="#313244",
    ),
    NodeSpec(
        node_type="remove_blank_pages",
        title="Remove Blank Pages",
        category="Organize",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        color="#313244",
    ),
    NodeSpec(
        node_type="nup_pdf",
        title="N-Up PDF",
        category="Organize",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"n": 2, "landscape": False},
        color="#313244",
    ),
    NodeSpec(
        node_type="linearize_pdf",
        title="Linearize",
        category="Organize",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        color="#313244",
    ),
    NodeSpec(
        node_type="sanitize_pdf",
        title="Sanitize",
        category="Organize",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={
            "remove_metadata": True,
            "remove_javascript": True,
            "remove_embedded": True,
            "remove_links": False,
        },
        color="#313244",
    ),

    # ── Edit ──────────────────────────────────────────────────────────────
    NodeSpec(
        node_type="watermark",
        title="Watermark",
        category="Edit",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"text": "DRAFT", "font_size": 48, "angle": 45, "opacity": 0.3},
        color="#2a2a3e",
    ),
    NodeSpec(
        node_type="add_page_numbers",
        title="Page Numbers",
        category="Edit",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"position": "bottom_center", "start_number": 1, "font_size": 10},
        color="#2a2a3e",
    ),
    NodeSpec(
        node_type="header_footer",
        title="Header/Footer",
        category="Edit",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={
            "header_center": "",
            "footer_center": "{page} / {total}",
            "font_size": 9,
        },
        color="#2a2a3e",
    ),
    NodeSpec(
        node_type="crop_pdf",
        title="Crop Pages",
        category="Edit",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={
            "margin_top": 0, "margin_bottom": 0,
            "margin_left": 0, "margin_right": 0,
        },
        color="#2a2a3e",
    ),
    NodeSpec(
        node_type="redact_pdf",
        title="Redact",
        category="Edit",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"search_terms": [], "whole_word": False},
        color="#2a2a3e",
    ),
    NodeSpec(
        node_type="flatten_pdf",
        title="Flatten",
        category="Edit",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"render_dpi": 150},
        color="#2a2a3e",
    ),
    NodeSpec(
        node_type="remove_annotations",
        title="Remove Annotations",
        category="Edit",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"annotation_types": None},
        color="#2a2a3e",
    ),

    # ── Convert ───────────────────────────────────────────────────────────
    NodeSpec(
        node_type="ocr_pdf",
        title="OCR",
        category="Convert",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"language": "eng", "dpi": 200, "skip_text_pages": True},
        color="#1e3a5f",
    ),
    NodeSpec(
        node_type="pdf_to_image",
        title="PDF → Images",
        category="Convert",
        inputs=[_pdf_in],
        outputs=[PortSpec("output_dir", "image", "Image Dir")],
        param_defs={"fmt": "png", "dpi": 150},
        color="#1e3a5f",
    ),
    NodeSpec(
        node_type="pdf_to_text",
        title="PDF → Text",
        category="Convert",
        inputs=[_pdf_in],
        outputs=[PortSpec("output", "text", "Text Out")],
        param_defs={"mode": "plain"},
        color="#1e3a5f",
    ),
    NodeSpec(
        node_type="image_to_pdf",
        title="Images → PDF",
        category="Convert",
        inputs=[PortSpec("inputs", "image", "Images In", multiple=True)],
        outputs=[_pdf_out],
        param_defs={"page_size": "image"},
        color="#1e3a5f",
    ),
    NodeSpec(
        node_type="office_to_pdf",
        title="Office → PDF",
        category="Convert",
        inputs=[PortSpec("inputs", "any", "Office Files", multiple=True)],
        outputs=[PortSpec("output", "pdf_dir", "PDF Out")],
        param_defs={},
        color="#1e3a5f",
    ),
    NodeSpec(
        node_type="pdf_to_excel",
        title="PDF → Excel",
        category="Convert",
        inputs=[_pdf_in],
        outputs=[PortSpec("output", "excel", "Excel Out")],
        param_defs={"fmt": "xlsx"},
        color="#1e3a5f",
    ),

    # ── Secure ────────────────────────────────────────────────────────────
    NodeSpec(
        node_type="compress_pdf",
        title="Compress",
        category="Secure",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"level": "med"},
        color="#3a1e5f",
    ),
    NodeSpec(
        node_type="encrypt_pdf",
        title="Encrypt",
        category="Secure",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"user_password": "", "owner_password": ""},
        color="#3a1e5f",
    ),
    NodeSpec(
        node_type="decrypt_pdf",
        title="Decrypt",
        category="Secure",
        inputs=[_pdf_in],
        outputs=[_pdf_out],
        param_defs={"password": ""},
        color="#3a1e5f",
    ),
]

_BY_TYPE: dict[str, NodeSpec] = {s.node_type: s for s in _SPECS}


def get_spec(node_type: str) -> NodeSpec | None:
    return _BY_TYPE.get(node_type)


def all_specs() -> list[NodeSpec]:
    return list(_SPECS)


def specs_by_category() -> dict[str, list[NodeSpec]]:
    out: dict[str, list[NodeSpec]] = {}
    for spec in _SPECS:
        out.setdefault(spec.category, []).append(spec)
    return out
