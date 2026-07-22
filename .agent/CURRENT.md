# CURRENT.md

## Active directive
- ID: D-20260722-1334-d006-task7-social-proposals
- Project directive: UMBRA-D-006
- Goal: Task 7 — soft social proposals + hybrid actuation wiring in runtime
- Status: done
- Acceptance: met — SocialEngine.propose wired into Organism.tick_once (recognize → resolve pendings → soft propose if not critical → arbitrate/govern → on SIGNAL execute create_pending); self/world/memory pinned to C0 when social_enabled owns condition; governance.admit(tick=) enables SIGNAL cooldown; 5 new tests + full suite green
- Touched files: umbra_core/runtime.py, umbra_core/self_model/engine.py, tests/test_d006.py, .superpowers/sdd/task-7-report.md, .agent/*
- Next action: Task 8 (per D-006 plan — see docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md)

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: f5d0421f3d17426199a7e2b8a811d87e
- Root-cause fix this task: `BodySchema.bootstrap()` caps tuple predated D-006 (missing SIGNAL_PLAY/SIGNAL_ASSISTANCE) → `SelfModel.capability_status()` defaulted them to "dormant" → `tick_once()`'s dormant-capability guard silently downgraded every social signal proposal to IDLE before governance ever saw it. Fixed by adding both capabilities to the bootstrap caps tuple.
- Order in tick_once: recognize+resume_pending (early, every tick) → arbitrate → dev bias → memory bias → social soft propose (only if `arbitrator.state.mode=="full"` and not `social_critical`) → world-model bias → self-model dormant/degraded guard → predict → govern (`admit(tick=self.tick)`) → execute → on admitted+executed SIGNAL_PLAY/SIGNAL_ASSISTANCE, `social.create_pending(...)` (fails soft on SocialEngineError/KeyError — no crash, no orphaned evidence)

## Last validation
- Command: pytest -q (mimir_validation_run BLOCKED: "validation requires an active observed task", same recurring precedent as Tasks 4/5/6)
- Result: 223 passed (tests/test_d006.py: 45 passed)

## Open blockers
- mimir_validation_run task-scoped runner unavailable (same precedent as Tasks 4/5/6) — validated locally via `pytest -q` instead
