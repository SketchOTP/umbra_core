# MicroPsi 2 — Track 1 evidence (UMBRA-D-000)

**Date:** 2026-07-20  
**Upstream:** https://github.com/joschabach/micropsi2 (MIT, `license.txt`)  
**Local clone:** `docs/prior-art/micropsi2/upstream/` (gitignored nested clone; not a foundation dependency)  
**Runnable check:** `python3 docs/prior-art/micropsi2/reproduce_modulators.py` → `OK micropsi_modulator_repro`

## Reproduction status (terminology correction)

```text
INDEPENDENT_MECHANISM_REPRODUCTION
```

`reproduce_modulators.py` is an **independent mechanism reproduction** of the Dörner/Psi modulator equations (and related need/WorldAdapter patterns audited statically). It is **not** a successful execution of the complete upstream MicroPsi2 runtime (server, Theano nodenet, UI). Full upstream runtime: **not executed** in Track 1.

## Scope evaluated

| Concern | Where it lives | What we saw |
|---|---|---|
| Drives / body needs | `Survivor` worldadapter (`island.py`) | Datasources `body-energy`, `body-water`, `body-integrity`; decay each tick; death at ≤0; eat/drink via datatargets |
| Motives / intentions | Global modulators `base_*` written by nodenet | Counts/importance/urgency of intentions and active motives feed emotional step |
| Emotional modulators | `DoernerianEmotionalModulators` in `stepoperators.py` | Derives `emo_activation`, pleasure, competence, securing_rate, resolution, selection_threshold from base motive stats |
| Action selection | Motive selection threshold + actor datatargets | `emo_selection_threshold = emo_activation`; actors write world datatargets (loco/eat) |
| Sensor / actor separation | `WorldAdapter` + Sensor/Actor nodes | Sensors read datasources (or modulators); actors write datatargets (or modulators); world updates between |
| Situated-agent loop | World + nodenet cycles | Explicitly async-tolerant: agents must handle lag between action and sensory confirmation |

## Architectural map (companion-relevant)

```text
[World]  Survivor datasources (energy/water/integrity)
    ↑↓ WorldAdapter (sensor values / actor commands)
[Nodenet] Sensor nodes ← datasources/modulators
          Motive/intention graph (agent-authored nets)
          DoernerianEmotionalModulators step (global emo_*)
          Actor nodes → datatargets/modulators
```

Emotion here is **cognitive modulation**, not a scripted “become happy” command — aligned with PROJECT_GOAL. Expression mapping (`emoexpression.py`) is a thin derived face of modulators + integrity.

## Stack reality

- Documented Python 3.4/3.5; pins Theano 0.7, old numpy/scipy, CherryPy/waitress.
- Full server/runtime is **not** a modern production foundation.
- Dict/Theano nodenet engines are research tooling around Psi theory, not a companion product runtime.

## Classification (Track 1)

| Piece | Class | Rationale |
|---|---|---|
| Dörner/Psi motive → emotion modulator equations | **adapt** | Non-LLM endogenous arousal/valence/competence; reproduced in stdlib harness |
| Sensor/Actor + WorldAdapter I/O split | **adapt** | Clean body/brain boundary for virtual↔physical transfer later |
| Survivor-style need datasources + decay/death | **adapt** | Causal homeostasis without commanded eat/sleep states |
| Full MicroPsi2 server / Theano nodenet / UI | **reject** (foundation) | Obsolete stack; do not build UMBRA on it |
| Node-net as sole cognitive substrate | **reference** | Useful theory; not required as UMBRA’s primary representation |
| `emoexpression` pain/joy mapping | **reference** | Optional expression layer; not the organism will |

## Gaps vs companion core

- No durable upgrade-safe identity / provenance product layer
- No longitudinal relationship / habit store
- Motive content still largely authored as nodenets (not developmental individuality out of the box)
- Fear formula incomplete (`todo` in upstream)
- Not a companion product runtime

## Next track

Homeostatic RL systems (order per D-000), then Hexis.
