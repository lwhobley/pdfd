"""Tool registry — discovers and registers all BaseTool subclasses."""
from __future__ import annotations
import importlib
import logging
import pkgutil
from typing import Iterator

from pdf_forge.tools.base import BaseTool, ToolMeta

log = logging.getLogger(__name__)

_TOOL_PACKAGES = [
    "pdf_forge.tools.organize",
    "pdf_forge.tools.edit",
    "pdf_forge.tools.convert",
    "pdf_forge.tools.secure",
]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def discover(self) -> None:
        """Import all tool subpackages and register BaseTool subclasses."""
        for pkg_name in _TOOL_PACKAGES:
            try:
                pkg = importlib.import_module(pkg_name)
            except ImportError as e:
                log.warning("Could not import tool package %s: %s", pkg_name, e)
                continue

            pkg_path = getattr(pkg, "__path__", [])
            for _, module_name, _ in pkgutil.iter_modules(pkg_path):
                full = f"{pkg_name}.{module_name}"
                try:
                    importlib.import_module(full)
                except Exception as e:
                    log.warning("Failed to load tool module %s: %s", full, e)

        # Register all BaseTool subclasses found after import
        for cls in _all_subclasses(BaseTool):
            if hasattr(cls, "meta") and isinstance(cls.meta, ToolMeta):
                self._register(cls)

    def _register(self, cls: type[BaseTool]) -> None:
        tid = cls.meta.tool_id
        if tid in self._tools:
            return
        self._tools[tid] = cls()
        log.debug("Registered tool: %s (%s)", tid, cls.meta.name)

    def get(self, tool_id: str) -> BaseTool | None:
        return self._tools.get(tool_id)

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def tools_by_category(self, category: str) -> list[BaseTool]:
        return [t for t in self._tools.values() if t.meta.category == category]

    def __iter__(self) -> Iterator[BaseTool]:
        return iter(self._tools.values())


def _all_subclasses(cls: type) -> list[type]:
    result = []
    for sub in cls.__subclasses__():
        result.append(sub)
        result.extend(_all_subclasses(sub))
    return result


# Singleton
registry = ToolRegistry()
