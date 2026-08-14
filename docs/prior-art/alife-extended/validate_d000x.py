import json
from pathlib import Path

ROOT = Path(__file__).parent
required = {
    "ALIEN", "Avida", "DISHTINY", "MABE2", "Evochora", "ASAL", "Lenia",
    "CAX", "Aevol", "Polyworld", "Stringmol", "Evo²Sim", "Ribossome", "Tierra"
}

def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

projects = load("project-matrix.json")
assert {p["project"] for p in projects} == required
assert len(projects) == 14
platform = load("platform-review.json")
assert {p["project"] for p in platform} == required
platform_keys = {"canonical_repository", "pinned_commit_or_release", "source_date", "license", "license_source", "primary_documentation", "primary_paper_if_applicable", "unit_of_life", "runtime_model", "identity_model", "learning_model", "environment_model", "persistence_model", "evolution_model", "umbra_overlap", "umbra_non_overlap"}
assert all(platform_keys <= set(p) for p in platform)
assert load("source-audits.json")[4]["project"] == "CAX"
assert load("license-matrix.json")[4]["project"] == "CAX"
assert load("duplication-map.json")
assert load("reuse-ledger.json")
for path in ROOT.glob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
forbidden_terms = ("TO" + "DO", "T" + "BD", "PLACE" + "HOLDER", "SOURCE_" + "VERIFICATION_PENDING")
for forbidden in forbidden_terms:
    hits = [str(p) for p in ROOT.rglob("*") if p.is_file() and forbidden in p.read_text(encoding="utf-8")]
    assert not hits, (forbidden, hits)
print("D-000X consistency: PASS")
