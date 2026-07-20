# PROJECT_PROFILE.md

## Identity
- Product: UMBRA — persistent organism/brain core for an autonomous digital pet companion
- Repo: UMBRA-CORE
- Mimir slug: umbra-core
- Serena project: UMBRA-CORE (`.serena/project.yml`)
- Source of truth: `.agent/PROJECT_GOAL.md`
- Github repo: TBD
- Github username: SketchOTP
- Github email: sketchotp@gmail.com

## What we are building
The persistent internal life of a believable digital companion (Digimon/Pokémon-class experience): identity, homeostasis, endogenous action, learning, development, memory, habits, relationships, temperament-from-history, embodied expression, and body transfer — without an LLM as the central controller and without scripted personality performance.

See `.agent/PROJECT_GOAL.md` for the full end-goal statement and success criteria.

## Architectural constraints (from PROJECT_GOAL)
- No LLM as central controller; optional language expresses, does not command
- No scripted emotional responses or predefined personality performances
- No user prompts required to remain active
- No direct commands: become happy, bond, eat, play, sleep, become afraid, etc.
- Behavior emerges from needs, regulation, body, memory, relationships, developmental history
- Must remain autonomous when no observer is present
- Bodies (avatar, robot, sensors, animations, dialogue) are interfaces around the organism core
- Digital chemistry / protocell research is optional and non-gating

## Program status
- Active project directive: **UMBRA-D-000** (prior-art reproduction and foundation selection)
- **UMBRA-D-000A rejected** — do not create or execute artificial-life/protocell substrate reframes
- **UMBRA-D-001 is blocked** until D-000 acceptance is met
- Canonical directive: `docs/directives/UMBRA-D-000-prior-art-reproduction.md`
- Prior-art lab notebook: `docs/prior-art/`
- Prior-art order: MicroPsi → homeostatic RL → Hexis → AEROS → AERA → PEPA → Soar/Hyperon (only if needed)
- Stance: informed reuse for the **companion organism core**; chemistry/protocell deferred

## Stack
- Target platform: Linux
- Implementation languages, persistence, and runtime: TBD pending D-000 selection ledger
- No UMBRA organism kernel yet — by policy, pending D-000
- Agent/tooling docs: Markdown, Cursor rules, Mimir V2, Serena

## Common commands
- Tests / build / CLI: stand up per-project as D-000 reproductions require
- Code navigation: Mimir V2 + Serena when code exists

<!-- MIMIR_PROJECT_BINDING_START -->
## Mimir binding
- Mimir project ID: 7777645d52a91b49
- Project name: UMBRA-CORE
- On every machine, call mimir_project_resolve with this ID and that machine's workspace path.
- Register only when this binding is absent; never create a host path or map a drive.
<!-- MIMIR_PROJECT_BINDING_END -->
