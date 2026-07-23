# CURRENT.md

## Active directive
- ID: D-20260723-0921-d008-task3-adapter
- Project directive: UMBRA-D-008
- Goal: Task 3 — EmbodimentAdapter attach/detach/swap + durable adapter-rejection routing through governance
- Status: complete — 4 brief-named tests + 3 supporting tests pass; full suite green (320 passed)
- Acceptance: EmbodimentAdapter attach/detach/swap emit embodiment_body_attached/detached/profile_swapped as AUTHORITATIVE events; execute() validates then delegates to Embodiment.execute_primitive or returns ok_raw=False rejection (no world mutation) for all 5 failure codes; Governance.execute_and_verify accepts optional adapter and routes through it; rejected outcome commits durably via the existing outcome_verified path; duplicate/replay of a rejection never executes the body
- Touched files: umbra_core/embodiment_adapters/adapter.py (new), umbra_core/embodiment_adapters/__init__.py, umbra_core/events.py, umbra_core/governance.py, umbra_core/runtime.py, tests/test_d008.py, .superpowers/sdd/task-3-report.md, .agent/*
- Next action: Task 4 — D-007→D-008 attachment migration (maybe_migrate_d008_attachment); wire Organism.embodiment_adapter construction into create_organism/load_organism

## Repo facts needed now
- Starting commit: bc7bfaa
- AdapterRequest/AttachmentState/EmbodimentAdapter are new in this task — no prior code referenced them
- EmbodimentAdapter.profile is resolved via an injectable profile_resolver (defaults to production get_profile); experiments (e.g. CONSTRAINED_TEST_BODY) pass a custom resolver rather than core importing experiments/
- Organism.embodiment_adapter defaults to None (backward compatible); create_organism/load_organism do not construct one yet — that is Task 4's migration responsibility
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: b456c87e513e45909ff31d8a1287f9f9 (Task 3 sub-task; parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 not closed — controller owns lifecycle)

## Last validation
- Command: pytest -q
- Result: pass (320 passed)

## Open blockers
- None for Task 3. Migration (Task 4), ExpressionEngine (Task 5+), and UI (Task 9) remain out of scope per this task's brief.
