# MABE2 harness comparison

Source review: `mercere99/MABE2` at `1fc9eb6`. The README describes a modular agent-based evolver built around Empirical; the pinned tree contains `source/`, `runs/`, `settings/`, `tests/`, `Planning/`, and `Makefile-base.mk`.

| UMBRA responsibility | MABE2 analogue | Recommendation |
|---|---|---|
| organism construction | modular agents/genomes | KEEP UMBRA authority; expose a narrow construction interface |
| conditions | settings/configuration | REFACTOR_INTERNAL around typed immutable conditions |
| scenarios | experiment modules/runs | ADAPT interface concepts |
| controls | agent/world modules | keep separate from authority and evidence |
| execution | experiment loop | REFACTOR_INTERNAL only after replay equivalence |
| metrics | analysis/statistics modules | modularize, but keep authoritative metrics typed |
| aggregation | run outputs | adapt schema and provenance pattern |
| validation | tests/experiment checks | retain UMBRA qualification gates |
| evidence generation | no direct UMBRA-equivalent authority | keep custom |
| verdict generation | no direct UMBRA-equivalent authority | keep custom and sealed |

Recommendation: `REFACTOR_INTERNAL`, not direct MABE2 integration. MABE2 can inform interfaces and module boundaries, but its evolutionary population semantics and dependency footprint add migration risk. The first infrastructure change should be a harness contract test proving organism construction, scenario, execution, metrics, aggregation, validation, evidence, and verdict are independently replaceable without changing a qualified result.
