# SOURCES — Homeostatic RL (Track 2)

Pinned 2026-07-20. Do not evaluate floating `main` without recording commit.

## P1 — Keramati & Gutkin (paper)

| Field | Value |
|---|---|
| title | Homeostatic reinforcement learning for integrating reward collection and physiological stability |
| authors | Mehdi Keramati, Boris Gutkin |
| publication | eLife |
| publication_date | 2014 |
| canonical_url | https://elifesciences.org/articles/04811 |
| repository_url | (none — paper equations) |
| exact_commit_hash | n/a (paper-only) |
| commit_date | n/a |
| license | CC-BY (eLife) |
| license_hash | n/a |
| runtime_dependencies | n/a |
| source_files_examined | formal reproduction of stated equations |
| claimed mechanism | vector internal state; drive; reward = drive reduction; deprivation; competition; overshoot; anticipation |
| mechanism actually present | equations present in paper; reproduced in `formal_reproduction/` |
| reproduction_status | INDEPENDENT_MECHANISM_REPRODUCTION (formal) |

## P2 — Continuous HRRL (paper)

| Field | Value |
|---|---|
| title | Continuous Homeostatic Reinforcement Learning for Self-Regulated Autonomous Agents |
| authors | (CTCS-HRRL arXiv authors) |
| publication | arXiv |
| publication_date | 2021 |
| canonical_url | https://arxiv.org/abs/2109.06580 |
| repository_url | (none audited in Track 2) |
| exact_commit_hash | n/a (paper-only) |
| license | arXiv non-exclusive distribution |
| claimed mechanism | continuous internal evolution; deterioration while inactive; anticipatory regulation |
| mechanism actually present | paper claims; formal env implements autonomous drift + anticipation proxy |
| reproduction_status | PAPER_REFERENCE + partial formal analogue |

## P3a — homeostatic_agents_pfrl

| Field | Value |
|---|---|
| title | Homeostatic Reinforcement Learning using PFRL |
| authors | Naoto Yoshida et al. |
| publication | Neural Networks 2024 (related) |
| canonical_url | https://github.com/ugo-nama-kun/homeostatic_agents_pfrl |
| repository_url | https://github.com/ugo-nama-kun/homeostatic_agents_pfrl |
| exact_commit_hash | `3d0a9b31ebec9dab8d24322e8bef8e639705ca74` |
| commit_date | 2025-06-28 +0900 |
| license | GitHub SPDX `NOASSERTION` (no LICENSE file in tree) |
| license_hash | n/a (absent) |
| runtime_dependencies | MuJoCo / mujoco-py, PFRL, torch; authors warn stack outdated |
| source_files_examined | `main_thermal.py`, `main_trp.py`, `main_vision.py`, `util/experiment.py`, `util/ppo.py`, `README.md` |
| source_hashes | see below |
| claimed mechanism | embodied thermal/resource homeostasis; drive-reduction reward comparison; multimodal obs |
| mechanism actually present | reward_setting ∈ {homeostatic, homeostatic_shaped, …}; training mains present |
| reproduction_status | UPSTREAM_RUNTIME_BLOCKED (mujoco_py/pfrl env); static audit OK |

### File hashes (SHA-256)

```text
main_thermal.py  3cea8d1af6ff432bcd34beb5fbafedd99a722c671ea2f89039206f3a8342a707
main_trp.py      acfa49a4d2efe933b364fee1c99f38a194156e9d4824a3c5fb267e4e2dc7fe37
util/experiment.py f422bbec3ff45a64dd83607a4e58b08d63410afc8cab4468b928974499f53604
util/ppo.py      ac78c4b11a800e1a344a0327a89dac3389a119457c82603fbb5dc54c11422ad0
README.md        8d194e2943af59d74894174a6390fad1fb146efbbaf9d8c1d58cbb3737ca085f
```

## P3b — deeprl_gfn

| Field | Value |
|---|---|
| title | Deep homeostatic RL for long-term nutritional strategies |
| authors | Naoto Yoshida et al. |
| canonical_url | https://github.com/ugo-nama-kun/deeprl_gfn |
| repository_url | https://github.com/ugo-nama-kun/deeprl_gfn |
| exact_commit_hash | `2f7af29311484bcc8f624359c7d60aa9a0cc64c9` |
| commit_date | 2024-11-22 +0900 |
| license | GitHub SPDX `NOASSERTION`; `LICENSE` file present but **empty** (0 bytes). Operator must not treat as confirmed MIT without clarifying upstream. |
| license_hash | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty file) |
| runtime_dependencies | gym==0.22.0, mujoco-py==2.1.2.14, pfrl==0.3.0, torch==2.0.1, Python 3.9 recommended |
| source_files_examined | `rules.py`, `train.py`, `visualize_behavior.py`, `trp_env/.../two_resource_env.py` |
| claimed mechanism | nutritional homeostasis; rule comparisons; homeostatic_shaped reward |
| mechanism actually present | `_homeostatic_shaped` = ‖d(prev)‖² − ‖d(curr)‖² drive-reduction form; nutrients blue/red |
| reproduction_status | FULL_ENV_BLOCKED (mujoco_py); SOURCE_DERIVED_EQUATION_SMOKE_OK |

### File hashes (SHA-256)

```text
rules.py              d45dab87879378741436b3022b1870a13cc1310fbdacb0d3a0c141fb701d1368
train.py              bd99a13b0c35fc0bbcf6e3f3ebe40bc9bfad21c7439f67ae6bdfc198f2091d94
visualize_behavior.py 7fcecc5b668918414c1db1b4f97f84f7a6c664e735d87be73f5c2cb07de98970
requirements.txt      71ce8dea82f841ea5667ae4af8c1ca45dcff5e77002fa5ca07fad1d744bb0faf
```

## P4 — Curiosity + homeostasis

Paper interaction only; no production recommendation in Track 2. Classification: `REFERENCE` (architectural interaction), not ADOPT.

## Deferred — multi-agent homeostatic coupling

Future Track 6 candidate. Not implemented in Track 2.
