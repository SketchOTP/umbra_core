# PEPA — Track 6 prior-art evaluation

**Status:** independent mechanism evaluation (not production UMBRA)  
**Paper:** [arXiv:2603.00117v3](https://arxiv.org/abs/2603.00117v3)  
**Project page:** https://sites.google.com/view/pepa-persistent/  
**Directive:** UMBRA-D-000 Track 6

## One-line result

PEPA’s **layered Sys1/Sys2/Sys3 autonomy loop** is useful after removing authored Big Five personality and LLM-generated motivation; those two are **rejected** as sources of individuality or organism will.

## What was evaluated

| Layer | PEPA claim | Public code | Independent test |
|---|---|---|---|
| Sys1 | Sensing, fixed skills, charging, nav, episodic record | Nav URLs blocked (HTTP 401) | Fixed skill repertoire + embodiment costs |
| Sys2 | Deliberation / MCTS / distilled policy | Not released | Drive-scored action selection + goal arbitration |
| Sys3 | Personality → goals/rewards + daily reflection | Prompts on site only | Deterministic bounded reflection (no LLM) |

## Verdict (preview)

See `docs/evidence/d000-track6/final-verdict.md`. Expected class: **PARTIAL_MECHANISM_QUALIFICATION**.

## Layout

```text
docs/prior-art/pepa/
  README.md
  SOURCES.md
  SOURCE_MAP.md
  UPSTREAM_REPRODUCTION.md
  ARCHITECTURE_DISSECTION.md
  COMPANION_RELEVANCE.md
  LIMITATIONS.md
  independent_reproduction/   # clean-room micro-world (not UMBRA kernel)
```

## Non-claims

This folder is **prior-art evidence only**. It is not a production UMBRA organism kernel, companion UI, or robotics deployment.
