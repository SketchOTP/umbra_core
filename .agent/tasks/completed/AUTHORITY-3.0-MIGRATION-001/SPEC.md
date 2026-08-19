# AUTHORITY-3.0-MIGRATION-001 — Specification

## Objective
Install the complete canonical Authority 3.0 repository governance package in UMBRA-CORE, adapted to verified UMBRA state, without deleting or rewriting legacy governance or scientific evidence.

## Goal relationship
Reliable governance protects the UMBRA mission by keeping Architect strategy, live repository truth, validation evidence, and acceptance boundaries synchronized while reducing repeated bulk context loading.

## Scope
- Root `AGENTS.md` Authority 3.0 router.
- `.agent/INDEX.md`, `EXTERNAL.md`, task structure, current/profile migration, and append-only migration records.
- `.agents/skills/authority/` workflow and references.
- Canonical `.agents/skills/external-discovery/SKILL.md`.
- UMBRA-specific Authority 3.0 validator coverage.
- Notion/GitHub closeout.

## Exclusions
- No UMBRA production, experiment, test semantics, thresholds, effects, formal evidence, verdict, tag, or scientific directive execution.
- No deletion or rewriting of historical directive/outcome/learning records.
- No formal P0 or D-013AP Phase A.

## Acceptance
- Every Authority 3.0 required repository file exists and is project-specific where required.
- Root router has no jCodemunch requirement and references only the 3.0 workflow.
- Exact old mutable snapshots and replaced discovery skill are preserved with verified hashes.
- Existing ledgers retain byte-identical historical prefixes and receive only new migration entries.
- `.agent/PROJECT_GOAL.md` and `.agent/LIBRARY_REVIEW.md` remain unchanged.
- Authority 3.0 validation and existing UMBRA governance validation pass.
- Repository diff contains governance-only changes.

## Risks
- Legacy ledgers use historical heterogeneous schemas; rewriting them would damage provenance.
- The old RECORD header prohibits agent edits, but the user explicitly authorized this governance migration. Any RECORD change must be one append-only governance event and must preserve the old text exactly.
- The v2 validator may encode assumptions not present in the 3.0 package.

## Stop conditions
- Any historical prefix, project goal, library review, production source, experiment, scientific test, threshold, verdict, evidence, or tag changes unexpectedly.
- Canonical package ambiguity would require inventing a strategic policy.
- Validation cannot distinguish active 3.0 rules from preserved legacy provenance.
