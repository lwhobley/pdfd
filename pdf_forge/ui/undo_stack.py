"""Undo/redo system for in-place PDF editing via command pattern."""
from __future__ import annotations
from abc import ABC, abstractmethod
import fitz
import logging

log = logging.getLogger(__name__)


class DocCommand(ABC):
    """Base class for operations that modify a PDF document."""

    @abstractmethod
    def execute(self, doc: fitz.Document) -> fitz.Document:
        """Apply the command to the document. Returns the modified document."""
        pass

    @abstractmethod
    def undo(self, doc: fitz.Document) -> fitz.Document | bytes:
        """Undo the command. Returns the document state before execute()."""
        pass

    @abstractmethod
    def description(self) -> str:
        """Short name for undo/redo UI."""
        pass


class SnapshotCommand(DocCommand):
    """Generic undo command restoring a serialized pre-edit document."""

    def __init__(self, description: str, before_bytes: bytes) -> None:
        self._description = description
        self._before_bytes = before_bytes

    def execute(self, doc: fitz.Document) -> fitz.Document:
        return doc

    def undo(self, doc: fitz.Document) -> bytes:
        return self._before_bytes

    def description(self) -> str:
        return self._description


class UndoStack:
    """Manages undo/redo for in-place PDF editing."""

    def __init__(self, max_undo_levels: int = 20) -> None:
        self._undo_stack: list[tuple[DocCommand, bytes]] = []
        self._redo_stack: list[tuple[DocCommand, bytes]] = []
        self._max_levels = max_undo_levels

    def push(self, command: DocCommand, before_state: bytes) -> None:
        """Record an already-applied command and its pre-edit byte snapshot.

        Args:
            command: The command to execute
            before_state: The document bytes before execution (for undo)

        Clears the redo stack (standard undo/redo behavior).
        """
        self._undo_stack.append((command, before_state))
        self._redo_stack.clear()

        # Cap the undo stack
        if len(self._undo_stack) > self._max_levels:
            self._undo_stack.pop(0)
            log.debug("Undo stack full; dropped oldest command")

    def undo(self, current_state: bytes) -> tuple[DocCommand, bytes] | None:
        """Pop the last command and save the outgoing state for redo.

        Returns:
            (command, bytes to restore) or None if nothing to undo
        """
        if not self._undo_stack:
            return None

        command, before_state = self._undo_stack.pop()
        self._redo_stack.append((command, current_state))
        return (command, before_state)

    def redo(self, current_state: bytes) -> tuple[DocCommand, bytes] | None:
        """Pop from redo and save the outgoing state for a later undo.

        Returns:
            (command, bytes to restore) or None if nothing to redo
        """
        if not self._redo_stack:
            return None

        command, before_state = self._redo_stack.pop()
        self._undo_stack.append((command, current_state))
        return (command, before_state)

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Clear all undo and redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def undo_description(self) -> str:
        """Description of what will be undone, for menu/tooltip."""
        if not self._undo_stack:
            return "Nothing to undo"
        cmd, _ = self._undo_stack[-1]
        return f"Undo: {cmd.description()}"

    def redo_description(self) -> str:
        """Description of what will be redone, for menu/tooltip."""
        if not self._redo_stack:
            return "Nothing to redo"
        cmd, _ = self._redo_stack[-1]
        return f"Redo: {cmd.description()}"
