"""Independent AXH protocol-preservation check.

This validator is intentionally metadata-only.  It verifies the frozen AX
protocol fingerprint and rejects production-runtime imports from the AXH
package; it never loads or executes an AX scientific target.
"""

from __future__ import annotations

import ast
from pathlib import Path

from .protocol import AX_PROTOCOL, protocol_fingerprint


EXPECTED_FINGERPRINT = "b3b065c2fcc06f9d1d7e4cdde59eac0b69919c9c31427f3f5456249c8c0cf07f"


def validate() -> dict[str, object]:
    package = Path(__file__).resolve().parent
    fingerprint = protocol_fingerprint(AX_PROTOCOL)
    if fingerprint != EXPECTED_FINGERPRINT:
        raise AssertionError(f"protocol fingerprint changed: {fingerprint}")

    forbidden_imports: list[str] = []
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name == "umbra_core" or name.startswith("umbra_core.") for name in names):
                forbidden_imports.append(f"{path.name}:{','.join(names)}")
    if forbidden_imports:
        raise AssertionError(f"production imports found: {forbidden_imports}")

    return {"protocol_fingerprint": fingerprint, "scientific_change_count": 0}


def main() -> None:
    result = validate()
    print(f"PASS protocol_fingerprint={result['protocol_fingerprint']} scientific_change_count=0")


if __name__ == "__main__":
    main()
