# CURRENT.md

## Active directive
- ID: D-20260723-0913-d008-task2-profiles
- Project directive: UMBRA-D-008
- Goal: Task 2 — production BodyProfile definitions, stable SHA-256 hashes, constrained test body, and thresholds hash amendment
- Status: complete — committed as 59ff69f; profile hashes are now real SHA-256 values
- Acceptance: brief-named tests pass; production profile hashes are real; constrained profile rejects at least one capability; commit and report written
- Touched files: tests/test_d008.py, umbra_core/embodiment_adapters/{__init__,profiles}.py, experiments/d008/{constrained_profile.py,thresholds.json}, .superpowers/sdd/task-2-report.md, .agent/*
- Next action: Continue later D-008 adapter/expression tasks

## Repo facts needed now
- Starting commit: bc7bfaa
- Preregistration freeze: experiments/d008/thresholds.json, experiment-matrix.json, scenario-suite.json
- Profile hashes: real SHA-256 values computed by `profile_definition_hash()` for `ABSTRACT_SHAPE_BODY` and `MINIMAL_CREATURE_BODY`
- Formal experiment execution remains blocked until later D-008 harness/adapter tasks; hash placeholders are no longer the blocker
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: 55618d5ddcce43d8bd50bd0c61be05a8 (Task 2)

## Last validation
- Command: pytest -q
- Result: pass (313 passed)

## Open blockers
- Formal D-008 experiments still wait for later adapter/expression harness tasks; production profile hashes are real
