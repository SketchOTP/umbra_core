"""Scan production umbra_core for runtime.tick / self.tick temporal dependencies.

Inventory source of truth: the current Q4 registry. The historical D-010
registry remains preserved and is not rewritten.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ROOT = REPO_ROOT / "umbra_core"
INVENTORY_PATH = Path(__file__).resolve().parent / "d010q4_runtime_tick_registry.json"


@dataclass(frozen=True)
class TickUseSite:
    """One classified production orchestration-tick dependency site."""

    site_id: str
    path: str
    line: int
    col: int
    kind: str
    symbol: str
    snippet: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "path": self.path,
            "line": self.line,
            "col": self.col,
            "kind": self.kind,
            "symbol": self.symbol,
            "snippet": self.snippet,
        }


def _iter_production_py_files() -> Iterator[Path]:
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        yield path


def _site_id(path: str, line: int, col: int = 0) -> str:
    return f"{path}:{line}"


def _snippet(source: str, line: int) -> str:
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return ""


def _enclosing_symbol(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    current: ast.AST | None = node
    while current is not None:
        if isinstance(current, ast.FunctionDef):
            return current.name
        if isinstance(current, ast.AsyncFunctionDef):
            return current.name
        current = parents.get(current)
    return "<module>"


class _TickUseVisitor(ast.NodeVisitor):
    def __init__(self, *, rel_path: str, source: str) -> None:
        self.rel_path = rel_path
        self.source = source
        self.sites: list[TickUseSite] = []
        self._parents: dict[ast.AST, ast.AST] = {}

    def visit(self, node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            self._parents[child] = node
        super().visit(node)

    def _record(self, node: ast.AST, *, kind: str) -> None:
        line = getattr(node, "lineno", 0) or 0
        col = getattr(node, "col_offset", 0) or 0
        symbol = _enclosing_symbol(node, self._parents)
        self.sites.append(
            TickUseSite(
                site_id=_site_id(self.rel_path, line, col),
                path=self.rel_path,
                line=line,
                col=col,
                kind=kind,
                symbol=symbol,
                snippet=_snippet(self.source, line),
            )
        )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "tick" and self.rel_path == "umbra_core/runtime.py":
            if isinstance(node.value, ast.Name):
                if node.value.id == "self":
                    self._record(node, kind="self.tick")
                elif node.value.id == "org":
                    self._record(node, kind="org.tick")
        self.generic_visit(node)

    def visit_keyword(self, node: ast.keyword) -> None:
        if node.arg in {
            "tick",
            "now_tick",
            "signal_tick",
            "prepared_tick",
            "derived_at_tick",
            "source_state_version",
            "runtime_tick",
        } and self._uses_self_tick(node.value):
            self._record(node, kind=f"kw:{node.arg}")
        self.generic_visit(node)

    def _uses_self_tick(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Attribute):
            return (
                isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and node.attr == "tick"
            )
        if isinstance(node, ast.IfExp):
            return self._uses_self_tick(node.body) or self._uses_self_tick(node.orelse)
        return False


def scan_production_runtime_tick_uses() -> list[TickUseSite]:
    """Return one site per source line (deduped) for inventory matching."""
    by_line: dict[tuple[str, int], TickUseSite] = {}
    for path in _iter_production_py_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        visitor = _TickUseVisitor(rel_path=rel, source=source)
        visitor.visit(tree)
        for site in visitor.sites:
            key = (site.path, site.line)
            existing = by_line.get(key)
            if existing is None or site.kind.startswith("kw:"):
                by_line[key] = site
    sites = list(by_line.values())
    sites.sort(key=lambda s: (s.path, s.line, s.col))
    return sites


def load_classification_inventory(
    inventory_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    path = inventory_path or INVENTORY_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    return {str(entry["site_id"]): entry for entry in entries}


def find_unclassified_uses(
    inventory_path: Path | None = None,
) -> list[TickUseSite]:
    inventory = load_classification_inventory(inventory_path)
    return [site for site in scan_production_runtime_tick_uses() if site.site_id not in inventory]


def validate_inventory(inventory_path: Path | None = None) -> list[str]:
    """Return human-readable validation errors (empty == ok)."""
    path = inventory_path or INVENTORY_PATH
    errors: list[str] = []
    if not path.is_file():
        return [f"missing inventory: {path.as_posix()}"]
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    inventory = {str(e["site_id"]): e for e in entries}
    for site in scan_production_runtime_tick_uses():
        entry = inventory.get(site.site_id)
        if entry is None:
            errors.append(f"unclassified: {site.site_id} ({site.snippet})")
            continue
        cls = entry.get("class")
        if cls not in {"O", "T", "B"}:
            errors.append(f"invalid class {cls!r} for {site.site_id}")
    stale = set(inventory) - {s.site_id for s in scan_production_runtime_tick_uses()}
    for site_id in sorted(stale):
        errors.append(f"stale inventory entry (no matching site): {site_id}")
    return errors


def main() -> int:
    sites = scan_production_runtime_tick_uses()
    unclassified = find_unclassified_uses()
    print(f"scanned {len(sites)} production tick dependency sites")
    if unclassified:
        print(f"unclassified ({len(unclassified)}):")
        for site in unclassified:
            print(f"  {site.site_id}  {site.kind}  {site.snippet}")
        return 1
    errors = validate_inventory()
    if errors:
        for err in errors:
            print(err)
        return 1
    print("inventory complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
