# UMBRA-CORE

UMBRA-CORE is a standalone, persistent autonomous-organism core for digital
companions. It is designed so behavior arises from internal regulation,
perception, learned causal models, verified consequences, memory, development,
relationships, individuality, temporal context, and environmental opportunity—not
from a chatbot loop or a scripted persona.

**Scientific status:** subsystem capabilities are qualified within explicit
boundaries; integrated long-horizon viability is **not qualified**. R6B is a
permanent negative generation, while the fresh R6B-R1 repair qualified a bounded
default-off verified route-control learning primitive: same-target `ORIENT` is
retained in route experience without becoming planning or action-selection
authority. R6C then qualified an additive, shadow-only planning-frame projection
for that route evidence and learned active affordances; it grants no planning or
action-selection authority.

[Project goal](.agent/PROJECT_GOAL.md) ·
[Current governed state](.agent/CURRENT.md) ·
[Evidence guide](docs/EVIDENCE_GUIDE.md) ·
[Reference architecture](docs/architecture/UMBRA_REFERENCE_ARCHITECTURE.md)

## Why this project exists

A believable persistent digital companion requires more than an LLM, a persona
prompt, a renderer, a scalar mood variable, or a scripted virtual pet. The harder
engineering problem is maintaining one causally coherent individual through time,
restart, learning, incomplete knowledge, relationships, competing internal needs,
changing environments, and changing bodies.

UMBRA explores that problem as an organism core: an autonomous runtime with explicit
state ownership, bounded learning, governed action, verified outcomes, durable
history, and evidence-limited claims.

## What UMBRA is not

UMBRA is not:

- an LLM agent or chatbot;
- a scripted pet or animation state machine;
- a renderer, avatar application, or robotics stack;
- a scalar mood, affection, loyalty, or survival optimizer;
- a digital chemistry, protocell, or biological-cell simulator;
- a claim of consciousness, sentience, emotion, or literal biological life.

Language, rendering, sensors, and physical or virtual bodies may surround the core,
but they must not become authoritative over organism identity, physiology, memory,
decision-making, or verified experience.

## Architecture

UMBRA separates the path that can authorize action from the internal systems that
supply state, evidence, and learned context. Those systems are causally relevant,
but they do not independently execute actions.

```mermaid
flowchart LR
    P["Policy-provenanced perception"] --> C["Candidate generation"]
    C --> A["Action selection / arbitration"]
    A --> G["Governance"]
    G --> E["Embodiment validation"]
    E --> X["Execution"]
    X --> V["Verified outcome"]
    V --> U["Bounded owner updates / learning"]

    H["Physiology"] --> C
    SM["SelfModel"] -. "body evidence" .-> A
    WM["WorldModel"] -. "learned consequence evidence" .-> A
    M["Memory and habits"] -. "history and continuity" .-> C
    D["Development"] -. "practice context" .-> C
    S["Relationships"] -. "partner-specific context" .-> C
    I["Individuality"] -. "history-shaped variation" .-> A
    T["Temporal continuity"] -. "time and commitments" .-> A
    HT["Habitat"] --> P

    U --> H
    U --> SM
    U --> WM
    U --> M
    U --> D
    U --> S
    U --> I
    U --> T
```

The central authority sequence is implemented in the runtime, arbitration,
governance, embodiment, persistence, and verified-outcome paths under
[`umbra_core/`](umbra_core/). The documents in [`docs/architecture/`](docs/architecture/)
describe the frozen foundation and should be read with the later result lineage in
the [evidence guide](docs/EVIDENCE_GUIDE.md); they are not a substitute for current
source and closeout records.

## Architectural principles

- **Persistent constitutional identity.** The organism remains the same individual
  across restart, migration, compatible body changes, and bounded true physical-body
  replacement.
- **Homeostatic regulation.** Physiology owns interacting regulatory state; other
  modules cannot write it directly.
- **Endogenous action.** Candidates arise from organism state, learned history, and
  current opportunity rather than direct user commands.
- **One governed authority path.** Candidate generation, selection, governance,
  embodiment validation, execution, verification, and learning remain distinct.
- **Learned SelfModel and WorldModel.** Body capability and environmental consequence
  models are revisable evidence, not self-authorizing truth.
- **Verified-consequence learning.** Proposals, denied actions, imagined futures, and
  renderer output do not count as lived outcomes.
- **Bounded history.** Memory, habits, development, relationships, and individuality
  are selective, provenance-bearing, and constrained in state and compute.
- **Temporal and habitat continuity.** Restart reconciliation preserves durable time
  and world relationships without fabricating unobserved experience.
- **Body independence.** A body is part of current experience, not constitutional
  organism identity.
- **Expression without control.** Renderers and optional language may express
  read-only state but may not become the organism's controller.
- **Reproducible but not mechanically identical.** Constitutional and persisted state
  are replayable; bounded stochasticity may contribute individuality where explicitly
  qualified.

## Current claim status

Statuses below are intentionally bounded. “Qualified” means the cited experiment or
contract passed its preregistered evidence boundary—not that the entire organism is
solved.

| Capability / property | Status | Evidence boundary |
|---|---|---|
| Persistent identity, autonomous runtime, and homeostasis | **QUALIFIED — bounded** | D-001 invariant companion-core qualification; not a long-horizon integrated viability claim. |
| Sensorimotor SelfModel | **QUALIFIED — bounded** | D-002 functional qualification plus separate D-002P performance remediation. |
| Predictive WorldModel | **QUALIFIED — bounded** | D-003 learned prediction/revision/planning-proposal evidence; not current planner authority. |
| Intrinsic development | **QUALIFIED — bounded** | D-004 competence, practice, satiation, and boundedness gates. |
| Selective long-term memory | **QUALIFIED — bounded** | D-005 episodic, semantic, procedural, consolidation, forgetting, and replay gates. |
| Partner-specific relationships | **QUALIFIED — bounded** | D-006 social contingency and history-dependent behavior. |
| Lived individuality | **QUALIFIED — bounded** | D-007 history-dependent divergence under controlled cohorts. |
| Coherent embodiment | **QUALIFIED — bounded** | D-008 body binding, profile transition, renderer separation, restart, and performance. |
| Persistent habitat agency | **QUALIFIED — bounded** | D-009 habitat authority, manipulation, persistence, and migration gates. |
| Temporal continuity | **QUALIFIED — current baseline** | D-010Q5 qualified the current baseline separately; earlier D-010 failures remain permanent. |
| Governed perception adapters | **QUALIFIED — bounded** | D-011 policy/provenance, rejection durability, replay, and boundedness. |
| True physical-body replacement | **QUALIFIED — bounded** | AS-003S atomic replacement transaction; see below. |
| Verified route-control learning | **QUALIFIED — bounded** | AS-003P-R6B-R1: one frozen nominal route-control acquisition plus one movement-slip failure leg; default-off, WorldModel-owned, no policy reader. |
| Route/affordance planning-frame projection | **QUALIFIED — bounded, shadow-only** | AS-003P-R6C: immutable V2 projection of exact V2 route experience and learned ACTIVE `inspect` affordances; historical route evidence is MAY-only and has no modal/action-selection reader. |
| Ordinary action selection and modal planning | **ACTIVE RESEARCH QUESTION** | Prior scalar and strict-dominance selectors were insufficient; modal planning remains shadow-only and has no behavior authority. |
| Integrated long-horizon viability | **NOT QUALIFIED** | Formal and long-horizon generations retain terminal failures; AS-004 and CLOSE-03 remain blocked. |

Detailed verdicts, manifests, and negative lineages are indexed in
[`docs/EVIDENCE_GUIDE.md`](docs/EVIDENCE_GUIDE.md).

## Recent result: atomic body replacement

AS-003S qualified a bounded true physical-body replacement transaction. The
implementation:

- preserves constitutional agent and lineage identity;
- mints a distinct physical `body_instance_id`;
- creates a new SelfModel body binding and schema;
- keeps EmbodimentAdapter and Embodiment occupancy coherent;
- commits one `embodiment_body_replaced` event and its prospective full snapshot in
  one SQLite transaction before applying live owner state;
- rolls back fully on pre-commit injection and recovers exactly after a
  commit-before-live-apply interruption;
- rejects stale body references, pending execution, and replacement while the old
  body holds an object;
- preserves memory, relationships, individuality, restart continuity, and later
  compatible profile-swap semantics.

The bounded lifecycle qualification performed one creation and one restart load with
zero organism ticks. Separate focused tests do exercise `tick_once()`; “zero ticks”
does not describe the entire test campaign. Focused AS-003S proofs passed `14/14`,
and baseline comparison found zero candidate-only failures in the applicable suite.

[AS-003S result](.agent/tasks/active/UMBRA-AS-003S/RESULT.md) ·
[validation summary](.agent/tasks/active/UMBRA-AS-003S/AS003S_VALIDATION_SUMMARY.json) ·
[crash-consistency proof](.agent/tasks/active/UMBRA-AS-003S/AS003S_CRASH_CONSISTENCY_PROOF.json) ·
[manifest](.agent/tasks/active/UMBRA-AS-003S/AS003S_EVIDENCE_MANIFEST.json)

## Recent result: same-target route-control learning

R6B-R1 repaired and freshly qualified the narrow route-experience boundary that
R6B exposed. A verified target-bound `ORIENT` now preserves continuity for the
same exact WorldModel opportunity and body schema, while its issue/completion
timing and provenance are retained as an ordered non-translational control step.
Verified translational `APPROACH` count remains separate. Unbound actions,
route switches, ambiguity, body changes, denials, and unverified outcomes still
fail closed; issued `IDLE` is an interruption.

The frozen assay acquired a nominal sequence containing three `ORIENT` steps,
one successful `APPROACH`, and terminal `CHARGE`, plus a separate verified
`movement_slip` failure leg. This is bounded route-learning evidence, not a
route planner, action-selection change, or integrated viability result. The
historical R6B failure remains permanent and is not rewritten.

[R6B-R1 task packet](.agent/tasks/active/UMBRA-AS-003P-R6B-R1/RESULT.md) ·
[R6B-R1 evidence guide entry](docs/EVIDENCE_GUIDE.md#as-003p-r6b-r1)

## Recent result: route and affordance planning-frame projection

AS-003P-R6C qualified an additive `AS003P_PLANNING_EVIDENCE_FRAME_V2` projection
without changing route learning, modal semantics, candidate generation, or
action-selection authority. A successful V2 route experience is joined only by
exact opportunity identity, body schema, and terminal capability; its ordered
verified control steps, observed duration, movement count, timing, and provenance
are exposed as `VERIFIED_OBSERVED_SUPPORT` with modality `MAY`. Failure history is
retained separately and cannot imply a future impossibility. V1 records remain
readable but are never upgraded with invented control steps.

The same frame can expose a policy-visible opportunity's learned `ACTIVE` inspect
affordance as `MAY`. Fixed authored priors, missing instances, weakened or
superseded beliefs, and unsupported joins remain `UNKNOWN`. The new fields are
deeply immutable, source-fingerprinted, bounded, deterministic, and ignored by
the existing modal evaluator; static analysis found zero readers in candidate
generation, arbitration, Governance, Embodiment, or planning/action-selection
authority. This is a planning-evidence substrate result, not a planner or
behavioral qualification.

[R6C result](.agent/tasks/active/UMBRA-AS-003P-R6C/RESULT.md) ·
[R6C evidence guide entry](docs/EVIDENCE_GUIDE.md#as-003p-r6c)

## Scientific method

UMBRA treats experiment design and negative evidence as part of the implementation:

- contracts, commands, thresholds, and stop conditions are preregistered or locked
  before qualification when the stage requires it;
- frozen failures terminate their generation—there is no post-hoc threshold
  weakening or silent retry;
- failed and inconclusive generations remain permanent evidence;
- formal qualification, bounded mechanism evidence, diagnostics, and static proofs
  are labeled separately;
- a passing test only supports the property it actually exercises;
- single seeds and demonstrations do not establish general viability;
- evidence artifacts use manifests, SHA-256 inventories, durable publication, and
  readback verification where required;
- current claims are reconciled across strategic authority, committed source, and
  retained execution evidence.

The repository's internal Authority 3.0 records live under [`.agent/`](.agent/) and
the active workflow is described by [`AGENTS.md`](AGENTS.md). These are governance
and provenance surfaces, not the recommended first entrypoint for understanding the
software.

## Selected negative results

Negative results are not removed when later work succeeds.

- **Temporal continuity:** historical D-010 performance generations failed. The
  current baseline was qualified later as a separate D-010Q5 generation rather than
  relabeling the old evidence.
- **Formal autonomy:** D-012B2 failed its remediated formal P0 when energy crossed the
  critical bound at tick 181. The broader D-012 viability claim remains unqualified.
- **Long-horizon viability:** D-014E1 completed eight fixed R0 runs but the
  preregistered R1 seed failed at tick 372 with critical fatigue; later populations
  were not run after the terminal stop.
- **Action selection:** AS-003C observed 2,647 qualifying ordinary multi-candidate
  decisions with zero supported-dominance eliminations and full-frontier saturation.
  AS-003D retired that strict-dominance architecture as a forward selector.
- **Route learning:** R6B's nominal leg failed when same-target `ORIENT` was treated
  as an unrelated interruption. R6B-R1 qualified the bounded repair while preserving
  the original failure as permanent evidence.
- **Observer measurement:** AS-003P/R1/R3 generations exposed import-protocol,
  comparator, and cross-run body-identity equivalence defects. Their raw modal traces
  were not promoted to qualified planning evidence. The body-identity defect found in
  that lineage led to the separately qualified AS-003S repair. AS-003P-R5 then created
  its one permitted zero-tick common root but stopped before forking because its frozen
  harness parsed a raw SQLite snapshot ID as JSON; no control/shadow branch ran.
  AS-003P-R5A separately reused that retained root under a new lock and established
  observer parity, but its fresh modal profiles supplied no candidate distinction,
  including across 57 relevant conflict exposures.

See [Selected negative evidence](docs/EVIDENCE_GUIDE.md#selected-negative-evidence)
for the exact records.

## Repository map

| Path | Purpose |
|---|---|
| [`umbra_core/`](umbra_core/) | Production organism core and owner modules. |
| [`tests/`](tests/) | Focused, regression, governance, and experiment-support tests. Some tests instantiate or tick organisms. |
| [`experiments/`](experiments/) | Diagnostic, preregistered, qualification, and retained-evidence harnesses. Read each stage contract before execution. |
| [`docs/architecture/`](docs/architecture/) | Frozen foundation architecture and authority references. |
| [`docs/evidence/`](docs/evidence/) | Committed historical result artifacts and verdicts. |
| [`research/`](research/) | Non-production research and course-correction tooling. |
| [`tools/`](tools/) | Governance, evidence, analysis, and bounded validation tools. |
| [`.agent/`](.agent/) | Internal source-of-truth router, current status, append-only outcomes, learnings, and task packets. |

## Local inspection and validation

The repository is Python and is currently exercised in place; [`pytest.ini`](pytest.ini)
adds the repository root to Python's import path. There is **no canonical root
`pyproject.toml`, requirements file, lockfile, or packaged installation procedure**.
Python and tool dependencies are therefore not yet presented as a reproducible public
bootstrap contract.

With a compatible Python environment in which `pytest` is already installed, focused
entrypoints include:

```bash
python3 -m pytest tests/test_as003s_body_replacement.py -q
python3 scripts/validate_authority_v3.py
python3 scripts/validate_governance.py --mode ADOPTED
```

These commands validate specific surfaces; they are not a substitute for a frozen
experiment protocol. Do not run an experiment merely because its module exists.
Historical harnesses carry stage-specific seeds, evidence roots, stop rules, and
authorization boundaries.

The repository does not currently claim a globally green full suite. At the AS-003S
closeout:

- focused AS-003S: `14 PASS / 0 FAIL`;
- D-002: `53 PASS / 1 inherited exact-baseline FAIL`;
- D-008/D-009: `202 PASS / 1 inherited D-009 FAIL / 2 SKIP`;
- path-safe applicable suite: `1120 PASS / 14 inherited FAIL / 2 SKIP`;
- candidate-only failures: `0`.

The raw full-suite collector also encounters an inherited orphan test import. These
results are evidence-accounting facts, not an “all tests passing” claim.

No root license is currently published. Treat the repository as available for review,
not as granting reuse rights, unless a license is added separately.

## Current research frontier

The body-replacement identity defect is closed within the AS-003S boundary. Bounded
hypothetical-state and modal-planning infrastructure exists, remains shadow-only, and
has not earned live action-selection authority.

AS-003P-R5A completed a prospectively locked common-root comparison from R5's retained
tick-0 state. One 500-tick CONTROL and one 500-tick SHADOW branch were semantically
equal across action timeline, candidate identities, authoritative events, final state,
Habitat, and RNG. This establishes observer-safe evidence acquisition for that pair.
The fresh shadow trace produced 500 complete frames and 2,686 candidate profiles, but
zero candidate-profile distinctions—including across 57 decisions exposing the
AS-003L residual conflict class. The terminal result is therefore
`AS003PR5A_OBSERVER_SAFE_MODAL_EVIDENCE_NONDISCRIMINATING`, not a planning
qualification.

AS-003P-R6 then examined those immutable traces without another organism run. It
confirmed that the top-level modal labels compress materially different immediate
consequences, but also found that the trace never retained source-backed route/service
demand. Under the preregistered AS-003L schedulability contract, all 5,323 admitted
modal witnesses therefore remain timing-unknown and no L2 candidate relation can be
supported. The terminal result is
`AS003PR6_SOURCE_EVIDENCE_INSUFFICIENT_FOR_L2`; it grants no planning authority.

R6A subsequently established that the missing route demand is not a lawful geometric
source join: radial opportunity distance and historical APPROACH support do not by
themselves form a guaranteed traversable route envelope. Its terminal result is
`AS003PR6A_ROUTE_DEMAND_LEARNING_PRIMITIVE_REQUIRED`. R6B is the bounded next step:
learn opportunity- and body-schema-bound route experience only from verified
execution outcomes, with no reader in action selection or planning. R6B is
permanently failed; R6B-R1 subsequently qualified same-target route-control
continuity. R6C now projects that qualified V2 evidence and learned ACTIVE
affordances into an immutable shadow frame, but the fields remain MAY/UNKNOWN
evidence and are not consumed by action selection.

The next planning experiment is recommendation-only. Planning integration,
AS-004 integrated viability, and CLOSE-03 final organism acceptance remain
blocked.

## Evidence navigation

Start with the [evidence guide](docs/EVIDENCE_GUIDE.md). It separates foundation
architecture, qualified subsystem verdicts, current status, selected negative results,
action-selection/planning research, and local/internal evidence provenance without
requiring access to private project conversations.
