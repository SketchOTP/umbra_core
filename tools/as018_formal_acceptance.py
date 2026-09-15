"""AS-018 P0 acceptance adapter over the hardened evidence validators."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.as017_formal_acceptance import accept_case as _accept_case


def accept_case(
    row: dict[str, Any],
    work: Path,
    candidate_commit: str,
    manifest_sha256: str,
    journal: Any,
) -> dict[str, Any]:
    """Apply the existing content/linkage checks and require AS-018 RRE trace scope."""
    if row.get("recovery_reachability_enabled") is not True:
        return {"verdict": "FAIL", "failures": ["rre_disabled_or_unrecorded"]}
    result = _accept_case(row, work, candidate_commit, manifest_sha256, journal)
    if result.get("verdict") != "PASS":
        return result
    trace = result.get("trace")
    if not isinstance(trace, dict) or trace.get("rows") != 7200:
        result["verdict"] = "FAIL"
        result.setdefault("failures", []).append("rre_trace_scope_invalid")
    result["schema"] = "AS018_FORMAL_CASE_ACCEPTANCE_V1"
    return result


__all__ = ["accept_case"]
