# UMBRA-AS-004 — terminal result

## Verdict

`AS004_KNOWN_R1_FAIL`

This is a terminal scientific failure of the frozen AS-004 generation, not a
protocol or harness failure. The implementation and pre-scientific gates passed;
the required known R1/S16 viability run reached its permitted terminal failure.

## Baseline and lock

- Starting baseline: `6da7326af2ff502bbf6bb712a08ae263b1505d54`
- Implementation commit: `c979356`
- Scientific execution lock: `ee9b06f`
- Evidence root: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-004-bounded-continuation-integrated-viability-r1/`
- Evidence manifest SHA-256: `ca0cd93b4effba187480ad36467ad62af4cb0c4e49a687a722e5808d3bd52ad6`

The frozen scientific source remained unchanged after the lock. Production
changes were confined to the authorized AS-004 implementation seam; no post-lock
production or test changes occurred.

## Pre-scientific evidence

- Protected lineage plus AS-004 focused proofs: `333/333 PASS`, twice identically.
- Compile, static authority, Authority 3.0, Governance, and `git diff --check`:
  PASS.
- Applicable repository regression: `1289 PASS / 2 SKIP / 13 inherited FAIL`;
  no candidate-only AS-004 regression was identified.
- The legacy ordinary WorldModel-plan lane and duplicate one-step option channel
  were bypassed only when the explicit AS-004 flag was enabled. Critical recovery
  authority remained separate.

## Frozen scientific sequence

Exactly one frozen command ran, with no retry or reseed. Diagnostic A and B
completed; the sequence stopped at the first required R1 terminal failure.

| Stage | Regime / seed | Horizon | Result | Continuation observations |
|---|---:|---:|---|---|
| Diagnostic A | R0 / `45878900` | 500 | `500/500` completed | 278 continuation decisions; O0 empty in 278; 0 eliminations |
| Diagnostic B | R0 / `22023239` | 3500 | `3500/3500` completed | 1751 continuation decisions; O0 empty in 1751; 0 eliminations |
| Known R1 | R1 / `57531938` | 7200 | terminal at tick `1929` | 946 continuation decisions; O0 empty in 946; 0 eliminations |

The R1 run first reached `NO_SAFE_ACTION` at tick `1928`, then terminated at
tick `1929` after a critical-failure boundary was reached. Physiology at the
terminal observation was energy `0.3555`, fatigue `0.9535`, integrity `0.9780`,
and stimulation `0.548`. The issued `REST` action produced a verified failed
outcome with reason `not_at_rest`; its recorded effects were energy `-0.003`
and fatigue `+0.002`.

## Stop boundary

The required historical blocker failed, so the frozen protocol correctly did not
run the fresh 32-run population, lifecycle qualification, accelerated 100k run,
real-time soak, or causal ablation. Organism runs: `3` diagnostic legs; control
and shadow runs: `0/0`; retries/reseeds: `0/0`.

Integrated long-horizon viability remains **NOT QUALIFIED**. AS-004 does not
authorize R7, CLOSE-03, or an automatic successor.

## Evidence limitation

The frozen runner retained durable summaries and SHA-256 values for the per-run
decision traces, then removed the dense traces after summarization. The terminal
failure result and causal first-failure payload are retained, but per-tick
continuation trace inspection is not available. This limitation is recorded and
was not repaired after the scientific lock.

## Primary records

- [AS-004 specification](SPEC.md)
- [AS-004 plan](PLAN.md)
- Terminal closeout evidence (local/internal):
  `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-004-bounded-continuation-integrated-viability-r1/AS004_TERMINAL_CLOSEOUT.json`
- Evidence manifest (local/internal):
  `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-004-bounded-continuation-integrated-viability-r1/AS004_EVIDENCE_MANIFEST.json`
