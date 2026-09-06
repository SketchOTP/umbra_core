"""Prepare and prove AS-013 downstream seed disjointness."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE")
REPO = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
SEED_RE = re.compile(r'(?i)(?:seed|base_seed|matched[^\n]{0,30}seed)\D{0,12}(\d{5,})')


def collect() -> set[int]:
    values: set[int] = set()
    paths = [REPO / ".agent", REPO / "experiments", REPO / "tests", REPO / "tools", EVIDENCE]
    for base in paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            if path.suffix.lower() not in {".json", ".jsonl", ".md", ".py", ".txt", ".toml"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            values.update(int(match) for match in SEED_RE.findall(text))
    return values


def main() -> None:
    historical = collect()
    candidates = {
        "boundedness": 91403101,
        "soak": 91403102,
        "ablation_base": 91403103,
        "preflight_boundedness": 39134001,
        "preflight_soak": 39134002,
        "preflight_ablation": 39134003,
    }
    formal_candidates = {name: value for name, value in candidates.items() if not name.startswith("preflight_")}
    overlaps = {name: value for name, value in formal_candidates.items() if value in historical}
    result = {
        "schema": "AS013_SEED_DISJOINTNESS_PROOF_V1",
        "directive": "UMBRA-AS-013",
        "baseline": "2723c50d1f06abcae60573307adfe83229def4a6",
        "historical_scan_roots": [str(REPO / ".agent"), str(REPO / "experiments"), str(REPO / "tests"), str(REPO / "tools"), str(EVIDENCE)],
        "historical_seed_count": len(historical),
        "selected": candidates,
        "formal_selected": formal_candidates,
        "overlaps": overlaps,
        "status": "PASS" if not overlaps else "FAIL",
    }
    out = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-013-publication-safe-boundedness-recovery-r1")
    out.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    path = out / "AS013_SEED_DISJOINTNESS_PROOF.json"
    path.write_text(rendered, encoding="utf-8")
    manifest = out / "AS013_DOWNSTREAM_SEED_MANIFEST.json"
    manifest.write_text(json.dumps({"schema": "AS013_DOWNSTREAM_SEED_MANIFEST_V1", "directive": "UMBRA-AS-013", "baseline": result["baseline"], "boundedness": {"seed": candidates["boundedness"], "ticks": 100000}, "soak": {"seed": candidates["soak"]}, "ablation": {"base_seed": candidates["ablation_base"], "regime": "R1/S16", "ticks": 7200, "variants": ["full", "terminal_readiness_disabled", "continuation_disabled", "route_learning_disabled"]}, "preflight": {"seeds": [candidates["preflight_boundedness"], candidates["preflight_soak"], candidates["preflight_ablation"]], "qualification": False}, "retries": 0, "reseeds": 0}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    registry = out / "AS013_HISTORICAL_SEED_REGISTRY.json"
    registry.write_text(json.dumps({"schema": "AS013_HISTORICAL_SEED_REGISTRY_V1", "directive": "UMBRA-AS-013", "historical_seed_count": len(historical), "seeds": sorted(historical)}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if overlaps:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
