"""UMBRA-D-000S synthesis acceptance tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GOAL = ROOT / ".agent" / "PROJECT_GOAL.md"
GOAL_MD5 = "d5f60b95f25145812300a5c18013f502"
SEAL = ROOT / "docs" / "evidence" / "d000-synthesis" / "track6-seal.json"
SYN = ROOT / "docs" / "evidence" / "d000-synthesis"
ARCH = ROOT / "docs" / "architecture"
D001 = ROOT / "docs" / "directives" / "UMBRA-D-001-invariant-companion-core.md"
PRODUCT_PATHS = [ROOT / "src", ROOT / "umbra", ROOT / "packages", ROOT / "kernel"]

REQUIRED_ARCH = [
    "UMBRA_REFERENCE_ARCHITECTURE.md",
    "ORGANISM_LOOP.md",
    "MODULE_AUTHORITY_MATRIX.md",
    "STATE_AND_EVENT_MODEL.md",
    "IDENTITY_AND_LIFECYCLE.md",
    "MEMORY_MODEL.md",
    "LEARNING_AND_PLANNING.md",
    "GOVERNANCE_AND_CAPABILITIES.md",
    "LLM_BOUNDARY.md",
    "OPEN_QUESTIONS.md",
]

MEMORY_TYPES = [
    "Working",
    "Episodic",
    "Semantic",
    "Procedural",
    "Relationship",
    "Strategic",
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_track6_is_sealed():
    seal = json.loads(SEAL.read_text())
    assert seal["track6_commit"] == "d55dbe1bd7fac8e1ab367c6fe203ba224606c7d4"
    assert seal["worktree_clean"] is True
    assert seal["tests_passed"] is True
    assert seal["gate0"] == "PASS"
    assert seal["project_goal_md5"] == GOAL_MD5
    tip = subprocess.check_output(
        ["git", "-C", str(ROOT), "cat-file", "-t", seal["track6_commit"]], text=True
    ).strip()
    assert tip == "commit"
    assert seal["mimir_task_id"]
    assert seal["evidence_hashes"]
    # hashes addressable
    for rel, digest in seal["evidence_hashes"].items():
        p = ROOT / rel
        assert p.is_file(), rel
        assert _sha(p) == digest, rel


def test_project_goal_unchanged():
    assert hashlib.md5(GOAL.read_bytes()).hexdigest() == GOAL_MD5
    seal = json.loads(SEAL.read_text())
    assert _sha(GOAL) == seal["project_goal_hash_sha256"]


def test_all_qualified_mechanisms_classified():
    ledger = json.loads((SYN / "mechanism-ledger.json").read_text())
    assert ledger["unresolved"] == []
    assert ledger["counts"]["unresolved"] == 0
    assert len(ledger["mechanisms"]) >= 80
    roles = {m["synthesis_role"] for m in ledger["mechanisms"]}
    assert "unresolved" not in roles
    assert ledger["soar_hyperon"] == "NOT_REQUIRED_NO_FOUNDATIONAL_GAP"


def test_all_architecture_decisions_have_evidence():
    conf = json.loads((SYN / "conflict-decisions.json").read_text())
    assert len(conf["conflicts"]) >= 18
    for c in conf["conflicts"]:
        assert c["decision"]
        assert c["accepted"]
        assert c["rejected"]
        assert c["evidence"]
        assert c["tradeoff"]
        assert c["risk"]
        assert c["revisit_condition"]
        # at least one evidence path exists or is under docs/
        assert any(str(e).startswith("docs/") or str(e).startswith(".agent/") for e in c["evidence"])


def test_every_module_has_single_authoritative_owner():
    matrix = (ARCH / "MODULE_AUTHORITY_MATRIX.md").read_text()
    assert "Forbidden writes" in matrix or "must not" in matrix.lower()
    audit = json.loads((SYN / "architecture-audit.json").read_text())
    owners = list(audit["module_owners"].values())
    assert len(owners) == len(set(owners))
    for name in REQUIRED_ARCH:
        assert (ARCH / name).is_file()


def test_learned_systems_cannot_grant_authority():
    text = (ARCH / "MODULE_AUTHORITY_MATRIX.md").read_text() + (
        ARCH / "GOVERNANCE_AND_CAPABILITIES.md"
    ).read_text()
    assert "never grant" in text.lower() or "cannot grant" in text.lower() or "may not" in text.lower()
    assert "capability grants" in text.lower() or "Capability grants" in text


def test_llm_is_not_required_for_core_loop():
    loop = (ARCH / "ORGANISM_LOOP.md").read_text()
    assert "without user prompts" in loop.lower() or "Must run without user prompts" in loop
    assert "LLM" in loop
    boundary = (ARCH / "LLM_BOUNDARY.md").read_text()
    assert "Rejected" in boundary or "rejected" in boundary.lower()
    assert "central controller" in boundary.lower() or "conscious" in boundary.lower()


def test_identity_excludes_personality_model_body_and_skills():
    ident = (ARCH / "IDENTITY_AND_LIFECYCLE.md").read_text()
    for word in ("personality", "memories", "model identity", "body identity", "skills", "mood", "preferences"):
        assert word in ident.lower() or word.replace(" ", " ") in ident
    assert "excludes" in ident.lower()


def test_memory_types_are_distinct():
    mem = (ARCH / "MEMORY_MODEL.md").read_text()
    for t in MEMORY_TYPES:
        assert t in mem or t.lower() in mem.lower()


def test_physiology_is_not_policy_writable():
    text = (ARCH / "GOVERNANCE_AND_CAPABILITIES.md").read_text() + (
        ARCH / "MODULE_AUTHORITY_MATRIX.md"
    ).read_text()
    assert "never write" in text.lower() or "may not write" in text.lower() or "not write" in text.lower()


def test_action_execution_requires_governance():
    gov = (ARCH / "GOVERNANCE_AND_CAPABILITIES.md").read_text()
    for stage in ("proposal", "capability admission", "policy", "contract", "runtime safety", "execution", "verified outcome"):
        assert stage in gov.lower() or stage.replace(" ", "") in gov.lower().replace(" ", "")


def test_clone_and_migration_are_distinct():
    ident = (ARCH / "IDENTITY_AND_LIFECYCLE.md").read_text()
    assert "clone" in ident.lower()
    assert "migration" in ident.lower()
    assert "new" in ident.lower() and "agent_id" in ident.lower()


def test_all_growth_paths_are_bounded():
    texts = "\n".join(p.read_text() for p in ARCH.glob("*.md"))
    assert "bound" in texts.lower()
    learn = (ARCH / "LEARNING_AND_PLANNING.md").read_text()
    assert "4" in learn and ("depth" in learn.lower())
    mem = (ARCH / "MEMORY_MODEL.md").read_text()
    assert "cap" in mem.lower() or "bound" in mem.lower()


def test_d001_contains_required_foundation():
    text = D001.read_text()
    audit = json.loads((SYN / "d001-audit.json").read_text())
    for mod in audit["required_modules_present"]:
        assert mod.lower() in text.lower()
    assert audit["audit_verdict"] == "D001_READY"
    assert audit["executable"] is True


def test_d001_excludes_deferred_features():
    text = D001.read_text().lower()
    audit = json.loads((SYN / "d001-audit.json").read_text())
    assert "deferred" in text
    for mod in audit["deferred_modules_excluded"]:
        assert mod.lower() in text


def test_no_production_kernel_created():
    for p in PRODUCT_PATHS:
        assert not p.exists(), f"unexpected production path {p}"
    # synthesis must not ship an umbra package tree
    assert not (ROOT / "umbra").exists()
    verdict = (SYN / "final-verdict.md").read_text()
    assert "UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED" in verdict
