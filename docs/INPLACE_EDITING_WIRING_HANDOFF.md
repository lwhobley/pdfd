# Handoff: Wire remaining tools to in-place editing

## Context

PDF'D is getting Adobe-style in-place editing: edits apply immediately to the
open document in memory, Ctrl+Z/Ctrl+Y undo/redo them, and Ctrl+S saves
in-place (save-as dialog on first save, silent save after that).

The infrastructure for this exists (`pdf_forge/ui/undo_stack.py`, dirty-state
tracking in `pdf_forge/ui/viewer/pdf_viewer.py`, `apply_to_doc()` methods on
most tool classes). **Only one tool — Rotate Pages — is actually wired into
the UI dispatch path**, and even that one had three crash/correctness bugs
that were just fixed (see "Bugs already fixed" below — read this before
copying the Rotate code as a template, it was broken).

Your job: wire the remaining ~19 tools that already have `apply_to_doc()`
methods into the same in-place path, following the corrected pattern below.

## Do this first: add the shared helper, don't copy-paste Rotate 19 times

The existing `_run_rotate_inplace()` in `pdf_forge/ui/main_window.py` hand-rolls
snapshot/undo/dirty/redraw logic inline (~45 lines) with a bespoke `RotateCommand`
class defined inline. Copying that per tool means copying its bug surface 19
times. Instead, add one shared helper to `MainWindow` and have each tool's
handler call it after collecting params from its dialog:

```python
def _apply_inplace_edit(self, tool_id: str, params: dict, description: str) -> bool:
    """Apply a tool's apply_to_doc() to the current tab's open document,
    with undo support, dirty tracking, and a re-render.

    Returns True if applied, False if there's no open document (caller
    should fall back to the legacy file-based flow in that case).
    """
    tab = self._current_tab()
    doc = self._viewer.current_doc() if tab else None
    if not tab or not doc:
        return False

    # fitz.Document wraps a SWIG/C object -- it is NOT copy.deepcopy-able
    # (raises TypeError: cannot pickle 'swig_runtime_data5.SwigPyObject').
    # Snapshot by serializing to bytes and reopening independently.
    before_bytes = doc.tobytes()

    tool = registry.get(tool_id)
    modified = tool.apply_to_doc(doc, params)

    # Almost all apply_to_doc() implementations mutate `doc` in place and
    # return the same object. repair_pdf is the one exception in the
    # current codebase (it built a new fitz.Document and closed the
    # original) -- see "repair_pdf" section below, which tells you to fix
    # it to mutate in place instead. If some future tool still returns a
    # different object, there is currently no adapter API to swap it into
    # the viewer (PyMuPDFAdapter.doc is a read-only property) -- do not
    # silently ignore `modified`; either add adapter support or make the
    # tool mutate in place like the others.
    assert modified is doc, (
        f"{tool_id}.apply_to_doc() returned a different document object; "
        "make it mutate doc in place instead (see repair_pdf fix below)."
    )

    from pdf_forge.ui.undo_stack import SnapshotCommand
    tab._undo_stack.push(SnapshotCommand(description, before_bytes), before_bytes)

    self._viewer.reload_from_memory()
    self._mark_dirty()
    self._update_undo_redo_buttons()
    self._status_bar.showMessage(description)
    return True
```

This needs a `SnapshotCommand` in `undo_stack.py` (`DocCommand.execute()` is
currently dead code — `UndoStack.push()` never calls it, only `undo()` is
ever invoked — so a single generic command class is enough; you don't need
per-tool command subclasses):

```python
class SnapshotCommand(DocCommand):
    """Generic undo command: restores a byte-snapshot taken before the edit."""

    def __init__(self, description: str, before_bytes: bytes) -> None:
        self._description = description
        self._before_bytes = before_bytes

    def execute(self, doc):
        return doc  # unused; UndoStack.push() never calls this

    def undo(self, doc):
        return self._before_bytes

    def description(self) -> str:
        return self._description
```

## Bugs already fixed this session (context, don't re-break these)

1. **`_save()` called `self._save_as_dialog()`, which didn't exist anywhere.**
   Every first save crashed with `AttributeError`. Fixed to use
   `QFileDialog.getSaveFileName()` directly.
2. **`doc.save(self._current_file_path)` crashed when saving back to the
   file the document was opened from** (`ValueError: save to original must
   be incremental`) — the exact "save in-place" case this feature exists
   for. Confirmed on Windows that a temp-file + `os.replace()` swap doesn't
   work either, because fitz keeps the source file locked open for the
   document's lifetime (`PermissionError`). Fixed: `doc.saveIncr()` when
   saving back to the original path, full `doc.save(...)` for save-as to a
   different path. See `_save()` in `main_window.py` for the working
   comparison logic (`os.path.normcase(os.path.normpath(...))`).
3. **`_run_rotate_inplace()` used `copy.deepcopy(doc)` for the undo
   snapshot, which crashes on every call** (`TypeError: cannot pickle
   'swig_runtime_data5.SwigPyObject' object` — fitz.Document isn't
   pickleable). Fixed to `fitz.open(stream=doc.tobytes(), filetype="pdf")`.
4. **`_undo()`/`_redo()` never actually restored anything.** They popped a
   `(command, before_state)` off the stack, showed a status message like
   "Undone: Rotate 90°", and called `reload_from_memory()` — but
   `reload_from_memory()` just re-renders whatever the document currently
   is. The document itself was never reverted, so Undo was a fake status
   message with no effect. **This is not yet fixed** — fixing it is part of
   this task, since every newly-wired tool depends on it working. See next
   section.

## You must fix `_undo()` / `_redo()` as part of this task

Currently (`main_window.py`, `_undo`/`_redo`):

```python
result = tab._undo_stack.undo()
if result:
    cmd, before_state = result
    doc = self._viewer.current_doc()
    if doc:
        self._viewer.set_dirty(True)
        self._viewer.reload_from_memory()   # <-- does nothing to the doc content
        self._status_bar.showMessage(f"Undone: {cmd.description()}")
        self._update_undo_redo_buttons()
```

`before_state` (with the `SnapshotCommand` above, a `bytes` blob) is never
applied back to `doc`. Fix by restoring the document's content in place —
verified working:

```python
doc.delete_pages(0, doc.page_count - 1)
doc.insert_pdf(fitz.open(stream=before_state, filetype="pdf"))
```

Do this in both `_undo()` and `_redo()` before calling `reload_from_memory()`.
Redo needs the same treatment — currently has the identical bug, using
whatever `before_state` the redo stack gives it (which after this fix will
also be `bytes`).

Also update the two call sites of `UndoStack.push()`/the tuple contents —
`_undo_stack.undo()`/`.redo()` return `(DocCommand, snapshot)` where
`snapshot` is now `bytes`, not a `fitz.Document`. `UndoStack` itself
(`undo_stack.py`) doesn't need changes — it's already snapshot-type-agnostic
(just stores whatever `push()` was given).

## Tool-by-tool wiring list

For each tool below: replace the legacy handler's file-based flow with a
branch that calls `_apply_inplace_edit()` first, falling back to the
existing file-based flow only when no document is open (same pattern as
`_run_rotate`: try in-place, `return` if it succeeded, otherwise fall
through to the legacy code already in the method — don't delete the legacy
code, it's the fallback for the "no doc open, dialog launched from an empty
window" case, which the app supports via `open_file` dialogs baked into
some flows).

Concretely, each handler goes from:

```python
def _run_watermark(self) -> None:
    input_path = self._require_open("Watermark")
    if not input_path:
        return
    dlg = WatermarkDialog(parent=self)
    if not dlg.exec():
        return
    out = self._save_as("Save Watermarked PDF", input_path, "_watermarked")
    if not out:
        return
    params = dlg.get_params()
    params.update({"input_path": input_path, "output_path": out})
    tool = registry.get("watermark")
    self._job_queue.submit(tool.create_job(params))
```

to:

```python
def _run_watermark(self) -> None:
    input_path = self._require_open("Watermark")
    if not input_path:
        return
    dlg = WatermarkDialog(parent=self)
    if not dlg.exec():
        return
    params = dlg.get_params()
    if self._apply_inplace_edit("watermark", params, "Watermark"):
        return
    out = self._save_as("Save Watermarked PDF", input_path, "_watermarked")
    if not out:
        return
    params.update({"input_path": input_path, "output_path": out})
    tool = registry.get("watermark")
    self._job_queue.submit(tool.create_job(params))
```

Note `params` for the in-place call does NOT include `input_path`/`output_path`
— `apply_to_doc()` only needs the tool-specific fields. Check each
`apply_to_doc()` signature in the tool file to see exactly which params keys
it reads (listed per tool below).

| tool_id | Dialog / params source | Legacy handler | apply_to_doc() params it reads | Notes |
|---|---|---|---|---|
| `watermark` | `WatermarkDialog.get_params()` | `_run_watermark` | `text, font_size, opacity, angle, color, pages` | |
| `add_page_numbers` | `PageNumbersDialog.get_params()` | `_run_page_numbers` | `start_number, prefix, suffix, include_total, position, font_size, color, skip_first` | |
| `bates_number` | `BatesDialog.get_params()` | `_run_bates` | `prefix, suffix, start_number, pad_width, position, font_size` | |
| `header_footer` | `HeaderFooterDialog.get_params()` | `_run_header_footer` | `header_left/center/right, footer_left/center/right, font_size, color, skip_first` | apply_to_doc's `{filename}` token resolves to the literal string `"document"` (no `input_path` available in-memory) — pre-existing limitation, not something to fix here unless you want to also wire `tab.handle.path` through as a `filename` override param |
| `crop_pdf` | `CropDialog.get_params()` (needs page W/H from `tab.handle.adapter.get_page_rect()`, see `_run_crop`) | `_run_crop` | `margin_top, margin_right, margin_bottom, margin_left, pages` | `pages` list built from `pages_mode` — keep that logic, just stop passing `input_path/output_path` |
| `redact` | `RedactDialog.get_params()` | `_run_redact` | `search_terms, fill_color, whole_word, case_sensitive` | `search_terms` built from splitting `p["search_term"]` on newlines — keep that |
| `edit_text` | `EditTextDialog.get_params()` | `_run_edit_text` | `find_text, replace_text, case_sensitive` | |
| `flatten_pdf` | `FlattenDialog.get_params()` | `_run_flatten` | `render_dpi` | |
| `remove_annotations` | `RemoveAnnotationsDialog.get_params()` | `_run_remove_annotations` | `annotation_types, pages` | |
| `delete_pages` | inline `QDialog` w/ `QLineEdit` + `_parse_page_spec()` | `_run_delete_pages` | `page_indices` | |
| `extract_pages` | inline `QDialog` w/ `QLineEdit` + `_parse_page_spec()` | `_run_extract_pages` | `page_indices` | |
| `reverse_pages` | none | `_run_reverse_pages` | (no params) | |
| `add_blank_page` | inline `QDialog` w/ `QSpinBox` | `_run_add_blank_page` | `position, width_pt, height_pt` | dialog only collects `position`; `width_pt`/`height_pt` default inside `apply_to_doc` |
| `remove_blank_pages` | none | `_run_remove_blank_pages` | (no params) | |
| `reorder_pages` | Page Organizer widget (drag-drop), **not** the Tools menu | `_organizer_apply` (different code path, around line 954) | `page_order` | Separate signal-based flow, not `_on_tool_requested`. Wire it the same way conceptually (`_apply_inplace_edit`) but you'll be editing `_organizer_apply` instead of a `_run_*` method |
| `repair_pdf` | none | `_run_repair` | n/a — **fix required first, see below** | |

### `repair_pdf` needs a fix before it can be wired

`pdf_forge/tools/secure/repair.py`'s `apply_to_doc()` currently does:

```python
def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
    dst = fitz.open()
    for i in range(len(doc)):
        dst.insert_pdf(doc, from_page=i, to_page=i)
    doc.close()
    return dst
```

This returns a **different** `fitz.Document` object and closes the original.
Every other tool's `apply_to_doc()` mutates `doc` in place and returns the
same object — the shared `_apply_inplace_edit()` helper above asserts on
that. There is currently no way to swap a new document object into
`PDFViewer`/`PyMuPDFAdapter` (`PyMuPDFAdapter.doc` is a read-only property
backed by `self._doc`, no setter). Fix `repair_pdf.apply_to_doc()` to mutate
in place instead, using the same delete-all-then-reinsert trick used for
undo restore:

```python
def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
    rebuilt = fitz.open()
    for i in range(len(doc)):
        rebuilt.insert_pdf(doc, from_page=i, to_page=i)
    doc.delete_pages(0, doc.page_count - 1)
    doc.insert_pdf(rebuilt)
    rebuilt.close()
    return doc
```

Then wire `_run_repair` the same way as the others.

### Tools that intentionally stay file-based (do not add apply_to_doc / do not wire)

These were evaluated and deliberately excluded — don't add in-place support
for them, the "Notes" column says why:

| tool_id | Why file-based only |
|---|---|
| `image_to_pdf`, `pdf_to_image`, `pdf_to_text`, `ocr_pdf`, `office_to_pdf`, `pdf_to_excel` | Convert tools produce a different file format or a brand-new document; there's no "in-place" version of "turn this PDF into a folder of PNGs" |
| `merge_pdfs`, `split_pdf`, `nup_pdf` | Fundamentally create a new document from N inputs or split one into many outputs — no single "current document" to mutate |
| `encrypt_pdf`, `decrypt_pdf` | Password/encryption handling happens via `pikepdf.Encryption` at save time; fitz has no in-memory encrypted-document concept to mutate |
| `compress_pdf` | Requires image downsampling + `pikepdf` save-time flags (`compress_streams`, `object_stream_mode`, etc.) that only apply at the moment of writing to disk |
| `linearize_pdf` | `linearize=True` is a `pikepdf.save()` flag, not a document mutation |
| `sanitize_pdf` | Requires low-level `pikepdf` dict manipulation (`/Names`, `/JavaScript`, docinfo) that fitz doesn't expose the same way |
| `sign_pdf` | Digital signatures go through `pyhanko`'s incremental PDF writer against a file handle, not an in-memory fitz document |

## Verification checklist

No GUI test harness exists for `MainWindow` (`qtbot` fixture errors out in
`tests/test_job_queue.py` — pre-existing, unrelated, don't try to fix it as
part of this task). Verify manually:

1. Run `python -m pdf_forge` (or however the app is normally launched), open
   a multi-page PDF.
2. For each newly-wired tool: run it via the Tools menu, confirm the page
   view updates immediately (no save dialog, no job spinner in the Jobs
   panel — in-place edits shouldn't go through `_job_queue` at all).
3. Ctrl+Z: confirm the document visibly reverts (not just a status message).
   Ctrl+Y: confirm it re-applies.
4. Ctrl+S on a document opened from an existing file: first save shows the
   save dialog; confirm you can save back over the *same* file without a
   crash (this was bug #2 above — test it explicitly, it's the main
   regression risk).
5. Close the tab / close the window with unsaved in-place edits: confirm the
   save-prompt dialog appears (already implemented, just confirm it still
   fires for the newly-wired tools).
6. Run `python -m pytest tests/ --tb=line` — expect `98 passed, 3 errors`
   (the 3 errors are the pre-existing `qtbot` issue, unrelated to this work).

## Files you'll touch

- `pdf_forge/ui/main_window.py` — add `_apply_inplace_edit()`, fix
  `_undo()`/`_redo()`, edit ~14 `_run_*` handlers + `_organizer_apply`.
- `pdf_forge/ui/undo_stack.py` — add `SnapshotCommand`.
- `pdf_forge/tools/secure/repair.py` — fix `apply_to_doc()` to mutate in
  place (see above).
