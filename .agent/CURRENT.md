# CURRENT.md

## Active directive
- ID: D-20260723-umbra-d008-coherent-digital-embodiment
- Project directive: UMBRA-D-008
- Goal: Coherent digital embodiment and nonverbal expression (Phase 2 body/habitat presentation)
- Status: in_progress — Task 1 preregistration frozen; profile hashes still PLACEHOLDER until Task 2
- Acceptance: Gates 0–14; QUALIFIED only with evidence; D-009 only under QUALIFIED
- Touched files: experiments/d008/{thresholds,experiment-matrix,scenario-suite}.json, .agent/CURRENT.md, .agent/REPO_MAP.md
- Next action: Task 2 — production body profiles + stable profile definition hashes; formal experiments must not run until hashes are real

## Repo facts needed now
- Starting commit: bc7bfaa
- Preregistration freeze: experiments/d008/thresholds.json, experiment-matrix.json, scenario-suite.json
- Profile hashes: PLACEHOLDER_COMPUTE_AT_FREEZE (Task 2 replaces with SHA-256 of canonical profile JSON)
- Formal experiment execution blocked until Task 2 hash freeze
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: a8c4dd2139ea4a88b5d40c132500344a (Task 1)

## Last validation
- Command: python -m json.tool experiments/d008/*.json
- Result: pending

## Open blockers
- Formal D-008 experiments blocked until production_profile_definition_hashes are real (Task 2)
