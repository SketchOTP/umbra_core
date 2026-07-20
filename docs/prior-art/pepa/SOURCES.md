# PEPA sources

## Paper

| Field | Value |
|---|---|
| Title | PEPA: a Persistently Autonomous Embodied Agent with Personalities |
| ID | arXiv:2603.00117 |
| Version audited | **v3** (abs/html/pdf) |
| Updated | 2026-05-07 |
| URL | https://arxiv.org/abs/2603.00117v3 |
| HTML | https://arxiv.org/html/2603.00117v3 |
| Authors | Kaige Liu, Yang Li, Lijun Zhu, Weinan Zhang |

## Project page

https://sites.google.com/view/pepa-persistent/

Contents audited: abstract, architecture figure description, Sys1 demo videos, personality prototype definitions (Lazy/Playful/Cautious/Working/Curious anchored to Big Five), charging demo, **Sys3 system prompts** for ultimate goals / daily goals / intrinsic reward updates.

## Repositories (publicly linked)

| Name | URL | Pin | License | Status |
|---|---|---|---|---|
| staircase_navi | https://anonymous.4open.science/r/staircase_navi-B38C | none | unknown | **HTTP 401** `not_connected` |
| elevator_staircase_navi | https://anonymous.4open.science/r/elevator_staircase_navi-1CC5 | none | unknown | **HTTP 401** `not_connected` |

GitHub / Hugging Face searches for `pepa-persistent`, `staircase_navi`, author+pepa: **0** public hits at audit time.

## Released vs missing

**Released (reachable):** paper; project-page prompts and narrative; demo videos (non-executable).

**Missing / unreachable:** full Sys3/Sys2 codebases; model weights; simulation harness; cloneable nav module commits; published license text for code.

## License

No reachable repository LICENSE file. Stance: `UNVERIFIED_NO_REACHABLE_REPO`.

## Hardware / models (from paper)

Hardware: Unitree Go2-W, Jetson Orin NX, Piper arm, Livox Mid-360, RealSense D405, multi-floor office.

Models: LLM (Sys3 + Sys2 MCTS), distilled dual-head BERT policy, YOLO button detector, SLAM/nav stacks.
