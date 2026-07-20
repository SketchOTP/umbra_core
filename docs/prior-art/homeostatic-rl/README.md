# Homeostatic RL — Track 2 (UMBRA-D-000)

**Status:** evaluated  
**Directive:** UMBRA-D-000 Track 2  
**Agent memory:** `D-20260720-umbra-d000-track2-homeostatic-regulation`  
**Does not authorize UMBRA-D-001.**

## Question

Which homeostatic RL mechanisms provide genuine causal motivation (internal state alters outcome value; satiation; competition; anticipation; autonomy under observer absence), versus scripted need selection or flat external reward maximization?

## Layout

| Path | Role |
|---|---|
| `SOURCES.md` | Pinned papers/repos, licenses, hashes |
| `FORMAL_MODEL.md` | Drive/reward equations used in formal repro |
| `UPSTREAM_REPRODUCTION.md` | Yoshida repo attempts + blockers |
| `MECHANISM_MATRIX.md` | Classifications |
| `COMPANION_RELEVANCE.md` | Companion-specific analysis |
| `FAILURE_MODES.md` | Pathologies + containment |
| `NOTES.md` | Lab notebook |
| `formal_reproduction/` | Dependency-light reference env + causal suite |
| `upstream/` | Gitignored clones (pinned commits in SOURCES) |

## Evidence

`docs/evidence/d000-track2/`

## Verdict (see `docs/evidence/d000-track2/final-verdict.md`)

Formal Keramati–Gutkin style mechanisms **qualify** under controlled tests. Upstream MuJoCo/PFRL stacks **blocked** for full runtime; source-derived `homeostatic_shaped` equations from `deeprl_gfn` **ran**. Production organism kernel: **not created**.
