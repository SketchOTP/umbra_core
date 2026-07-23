# UMBRA-D-008 Design: Coherent Digital Embodiment and Nonverbal Expression

**Date:** 2026-07-23  
**Project directive:** UMBRA-D-008  
**Agent memory directive:** `D-20260723-umbra-d008-coherent-digital-embodiment`  
**Starting commit:** `bc7bfaa`  
**Prerequisite:** `UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED`  
**Mimir project:** `7777645d52a91b49`  
**Mimir task:** `cbbb61834c98463cb70fb9254ba08ea2`  
**Status:** Design frozen; proceed to implementation planning after user review

## Purpose

Give the qualified D-001…D-007 organism core a **body-independent digital embodiment layer** so UMBRA is visibly present in a persistent virtual habitat. Visible behavior must causally reflect internal condition, authorized actions, learned individuality, and environmental interaction — not authored personality scenes or animation schedules.

## Locked decisions (operator-approved)

1. **Reference surface:** Dependency-free **Tkinter** reference companion over a **headless presentation model**. Tkinter visualizes authoritative state; it does not participate in organism control, persistence, or scientific evaluation logic.
2. **Adapter:** Thin governed **`EmbodimentAdapter`** enforces body-profile capability constraints and delegates all authoritative world mutation to existing **`Embodiment`**.
3. **Presentation authority:** Derivable **`PresentationState`** with a bounded, rebuildable, **non-authoritative frame ring** for rendering, interpolation, diagnostics, and latency measurement. Frames are never event-sourced and never snapshotted.
4. **Body profiles:** Two fully compatible production profiles (`ABSTRACT_SHAPE_BODY`, `MINIMAL_CREATURE_BODY`) plus one isolated experimental `CONSTRAINED_TEST_BODY` under `experiments/d008/`.
5. **Runtime shape:** Side-car expression loop — preserve D-001…D-007 tick order except routing governed embodiment execution through the adapter; derive after committed outcomes; renderers poll independently.
6. **Capabilities:** Use repo names only (`IDLE`, `ORIENT`, `MOVE`, `APPROACH`, `RETREAT`, `INSPECT`, `REST`, `CHARGE`, `SIGNAL_PLAY`, `SIGNAL_ASSISTANCE`). Do not invent `MAINTAIN`/`PRACTICE` capabilities. `CHARGE` presents maintenance/recovery; development practice goals present as their selected existing capability.
7. **Import rule:** `core` / `experiments` never import `ui/`. `ui/` may import presentation interfaces from `umbra_core.expression`.

## Hard constraints

* No LLM controller; no mood/emotion/personality authority in production.
* No scripted animation playlist, emotional scenes, engagement timers, or random emotional scenes as C0 autonomy.
* Expression / adapter / renderer must not grant capabilities, write physiology/memory/identity/relationships, invent success, or bypass governance.
* Graphics quality is not a scientific objective.
* No chemistry/protocell, robotics, camera, microphone, or language prerequisites.
* Closing or hiding the UI window must not stop UMBRA.
* Detached body: explicit empty presentation; never fabricate a body or replay last pose as current truth.

## Scientific claims

**Authorized (bounded):** coherent, body-independent digital embodiment in which visible behavior and nonverbal expression causally reflect the persistent organism’s internal condition, authorized actions, learned individuality, and environmental interaction.

**Not authorized:** consciousness, subjective experience, genuine emotion, biological life, human-equivalent expression, complete companion capability, physical embodiment readiness, natural-language understanding.

---

## 1. Architecture & packaging

```text
umbra_core/expression/
  presentation_state.py
  engine.py                 # ExpressionEngine
  frame_ring.py
  renderer.py               # ReferenceRenderer protocol
  headless_renderer.py

umbra_core/embodiment_adapters/
  adapter.py                # EmbodimentAdapter
  profiles.py               # ABSTRACT_SHAPE_BODY, MINIMAL_CREATURE_BODY

ui/reference_companion/
  tkinter_renderer.py
  habitat_view.py
  diagnostics.py

experiments/d008/             # C1–C10, CONSTRAINED_TEST_BODY, harnesses, freeze
tests/test_d008.py
docs/evidence/d008/
```

### Runtime pipeline

```text
organism tick (D-001…D-007 order preserved)
  → arbitration → governance
  → EmbodimentAdapter.execute(request, body_profile)
       ├─ validate capability support / physical limits
       ├─ translate body-neutral request
       └─ Embodiment.execute(...)   # sole habitat/body mutation
  → verified execution outcome committed
     (adapter rejection = verified failed outcome BEFORE derive)
  → ExpressionEngine.derive(...)    # every tick, including no-action
  → bounded frame ring (+ RenderPacket)
```

Renderers poll independently:

```text
HeadlessRenderer | TkinterRenderer
  → frame_ring.read_latest(renderer_cursor)   # non-destructive
```

### Ownership

| Layer | Owns | Must not |
|-------|------|----------|
| Organism core | identity, needs, action, learning, memory, habits, relationships, individuality, governance, capability authorization | present, animate, mood |
| ExpressionEngine | semantic presentation derivation, transition intent, source refs, condition channels | select actions; write core; own canvas interpolation |
| FrameRing | bounded non-authoritative frames | influence action/phys/memory/identity/world |
| EmbodimentAdapter | attach/detach/swap, profile limits, request translation, outcome reporting | mutate world/phys/memory/identity/relationships; invent success; authorize via cosmetics |
| Embodiment | habitat truth, collision, movement, observations | personality; presentation authority |
| Renderer | visual interpolation, UI layout, cosmetic motion (local wall time) | write organism state; set goals; schedule autonomy |

### Semantic transitions vs visual interpolation

* ExpressionEngine derives fields such as `previous_posture`, `target_posture`, `transition_kind`, `transition_started_tick`, `transition_source_state_version`, `transition_duration_ticks_hint`.
* Renderer performs pixel/canvas interpolation and cosmetic secondary motion.
* ExpressionEngine does not own frame-rate-specific animation timing.

### Production vs experimental profiles

**Production** (full capability set): `ABSTRACT_SHAPE_BODY`, `MINIMAL_CREATURE_BODY`.  
May differ in geometry, scale, posture mappings, orientation indicators, signal presentation, movement interpolation, turn rate, acceleration, cosmetic motion, visible condition mappings. Minor physical differences must not materially prevent continuity testing.

**Experimental only:** `CONSTRAINED_TEST_BODY` — rejects ≥1 capability, imposes meaningful movement/turn limit, omits ≥1 presentation feature, produces normal adapter failures, never mutates world on rejection.

---

## 2. State & authoritative events

### PresentationState (derived; not snapshotted)

```text
body_instance_id
body_profile_id
attachment_status
position                    # null when DETACHED
orientation                 # null when DETACHED
locomotion_state
posture                     # null when DETACHED; else NEUTRAL|ACTIVE|OBSERVING|
                            # RESTING|RECOVERING|WITHDRAWN|INTERACTING|INTERRUPTED
attention_target
attention_confidence
active_capability           # null when DETACHED
action_phase                # UNAVAILABLE when DETACHED
interaction_target
rest_activity_state
visible_condition_channels  # speed, persistence, compression, rest freq,
                            # orientation stability, transition speed,
                            # maintenance condition, activity intensity,
                            # attentional persistence
developmental_markers
nonverbal_signal            # null when DETACHED
previous_posture
target_posture
transition_kind
transition_started_tick
transition_source_state_version
transition_duration_ticks_hint
source_event_refs           # bounded count; prioritized; validated; no payload copy
```

No wall-clock fields in semantic presentation state. No mood/emotion/personality fields.

### Frame ring entry (non-authoritative) — stores coherent RenderPacket

```text
FrameRingEntry
  frame_id
  derived_at_tick
  active_execution_id         # null valid for rest/observe/recover/wait
  render_packet
    presentation_state
    habitat_read_model        # immutable, bounded; captured at derive time
    source_state_version
    habitat_state_version
    body_attachment_generation
  source_event_refs
```

Fixed max size and retention. Restart clears or rebuilds from current authoritative state. Backpressure drops stale frames; never blocks core.

The habitat read model is projected **once at derive time** into the packet and stored in the ring. Renderers must **not** reconstruct habitat later when polling — that would risk pairing an older presentation with newer habitat truth.

**Stale rejection:** generation mismatch always invalidates; state-version mismatch invalidates superseded frames; obsolete execution ID invalidates frames claiming that execution; null execution ID remains valid for state-derived frames. Incoherent packets (version/generation mismatch inside the packet) are dropped, never displayed.

### Authoritative attachment state

Persisted:

```text
body_instance_id
body_profile_id
attachment_status
attachment_generation
```

Profile definitions are static configuration (not duplicated into every event):

```text
supported_capabilities
physical_limits
presentation_mapping
profile_schema_version
profile_definition_hash
```

Events record selected `profile_id`, `profile_schema_version`, and `profile_definition_hash`.

### Authoritative events

```text
embodiment_body_attached
  old_status: DETACHED → ATTACHED
  new_body_instance_id, new_profile_id, new_generation
  profile_schema_version, profile_definition_hash
  origin                          # e.g. NORMAL | D008_MIGRATION

embodiment_body_detached
  body_instance_id, profile_id
  old_generation → new_generation
  reason
  (+ schema/hash as applicable)

embodiment_body_profile_swapped
  body_instance_id (normally retained)
  old_profile_id → new_profile_id
  old_generation → new_generation
  profile_schema_version, profile_definition_hash
```

Rules:

* every attach/detach/swap increments `attachment_generation`;
* swap is atomic;
* duplicate event application is idempotent;
* invalid generation order fails closed;
* world mutation and attachment-event commit cannot partially succeed;
* compatible swap retains `body_instance_id`; true replacement uses detach+attach;
* missing authoritative embodiment events fail closed on replay **after** migration (below);
* expression frames are never authoritative events and never appear in organism snapshots.

### D-007 → D-008 attachment migration

Qualified pre-D-008 organisms lack attachment events. First D-008 startup must migrate once — not treat missing attachment as corruption.

```text
D008 attachment migration
  detect pre-D008 schema
  read existing authoritative Embodiment state
  select the frozen default production profile
  create attachment state
  append embodiment_body_attached (origin = D008_MIGRATION)
  record migration source version
  commit atomically
```

Rules:

* migration is idempotent;
* runs only for a recognized pre-D008 schema;
* `body_instance_id` is stable after migration;
* profile ID, schema version, and definition hash are recorded;
* no memory, individuality, relationship, physiology, or habitat state resets;
* after migration, missing attachment events fail closed normally;
* birth replay includes the migration attachment event rather than rerunning inference;
* use `embodiment_body_attached` with `origin = D008_MIGRATION` — no separate event type.

### Adapter rejection — durable failed execution outcome

```text
governance permits request
→ adapter rejects unsupported capability or physical constraint
→ commit durable failed execution outcome
→ no Embodiment.execute call
→ no world mutation
→ derive INTERRUPTED / inability presentation
```

Failed outcome fields:

```text
execution_id
request_id
body_instance_id
body_profile_id
attachment_generation
capability
failure_code
profile_constraint
tick
```

Stable failure codes:

```text
UNSUPPORTED_BODY_CAPABILITY
BODY_LIMIT_REJECTED
BODY_DETACHED
STALE_ATTACHMENT_GENERATION
PROFILE_HASH_MISMATCH
```

Duplicate replay must be idempotent. A crash must not leave a rejected request without its failed outcome or allow it to execute after restart.

### Detached derivation

```text
attachment_status = DETACHED
active_capability = null
action_phase = UNAVAILABLE
position = orientation = posture = nonverbal_signal = null
```

Organism core may continue; renderer shows empty body layer; habitat may still render.

---

## 3. Reference UI & habitat view

### ReferenceRenderer protocol (`umbra_core.expression.renderer`)

```text
read_latest(frame_ring, renderer_cursor) → newest valid FrameRingEntry
render(entry.render_packet)
set_diagnostics_visible(bool)   # UI-only
close()                         # unregister cursor; destroy local resources only
```

* Polling is **non-destructive** (per-renderer cursor / last-seen `frame_id`).
* Habitat comes from `entry.render_packet.habitat_read_model` — never re-projected at poll time.
* Cadence independent of organism ticks.
* Renderer failure/closure/slowdown must not pause the organism.
* Exceptions contained and recorded diagnostically.

### TkinterRenderer lifecycle

`close()` must: unregister frame cursor; destroy only window resources; stop renderer-local polling; leave organism, adapter, ExpressionEngine, and HeadlessRenderer untouched.

Organism tick must not be forced onto the Tk main thread. Use a thread-safe bounded handoff / poll boundary. Tkinter callbacks must not invoke organism mutation.

### Habitat read model

View of authoritative embodiment/world state. Presents organism (from PresentationState), zones, objects, rest location, partners when present, environmental state, proximities, authorized habitat changes. Must not invent entities or write state. Absent habitat entities disappear from the view.

### Inhabited-world vs diagnostics

**Habitat canvas:** geometry, orientation, posture, attention markers (only above frozen confidence), nonverbal icons, environment. Not a status dashboard.

**Diagnostics (optional):** capability, phase, versions, source refs, condition channels. Removable without changing inhabited-world or organism behavior.

Cosmetic motion uses renderer-local wall time only; resets after renderer restart; never replayed as autonomy; never counted as individual behavior.

---

## 4. Experiments & gates

### Preregistration (commit + hash before formal execution)

```text
experiments/d008/thresholds.json
experiments/d008/experiment-matrix.json
experiments/d008/scenario-suite.json
```

Must include `minimum_gate_critical_paired_seeds = 100` applying **separately** to every Gate 1–10 comparison cell. Exploratory cells may use fewer seeds but cannot support qualification claims.

**Also freeze explicitly:**

* exact hashes of both production body profiles (`ABSTRACT_SHAPE_BODY`, `MINIMAL_CREATURE_BODY`);
* default migration profile ID;
* frame-ring capacity and retention;
* habitat read-model bounds;
* renderer cadence;
* attention-confidence display threshold;
* Tkinter diagnostic-panel state for soak comparison;
* real-display or virtual-display configuration;
* adapter rejection failure codes (full set above).

### Conditions

| C | Role |
|---|------|
| C0 | Full causal embodiment + expression (production path) |
| C1 | Scripted animation scheduler disconnected from core |
| C2 | Random presentation changes |
| C3 | Direct scalar mood→animation controller |
| C4 | Actions execute; presentation ignores them |
| C5 | Presentation ignores learned individuality |
| C6 | Presentation ignores physiology |
| C7 | Isolated hostile renderer/test-double attempting prohibited writes (must be impossible or rejected without state change). Do **not** give production renderer a mutable organism reference. |
| C8 | Body-profile change resets presentation **and** organism history — disposable experimental DBs only; never sealed/production history |
| C9 | Expression frames temporally shuffled |
| C10 | **Performance baseline:** same organism scenario with ExpressionEngine and renderers disabled. Measures core-only CPU/RSS and incremental expression/Tkinter cost. Not a scientific failure of embodiment coherence. Gates 1–10 primarily use C0–C9. |

C1/C2/C3/C7/C8 must not share production authority or persistence schemas with C0.

### Scenarios S0–S12

Environment/opportunity manipulation only; never command expression state. Coverage: autonomous habitat; fatigue→rest→recovery; explore/inspect; failed/blocked capability; uncertain observation; partner signal; withdrawal; habit/routine; D-007 history contrast; partner absence; restart mid-activity; body swap; extended no-user.

### Gates

| Gate | Focus |
|------|--------|
| 0 | Prior D-001…D-007 seals unchanged |
| 1 | Action–expression coherence; C0 materially outperforms C1,C2,C4,C9 |
| 2 | Condition–expression coherence; C6 worse; no mood authority |
| 3 | Attention coherence; uncertain stays ambiguous |
| 4 | Individuality expression; C5 reduces between-history separation |
| 5 | Autonomous presence; rest/inactivity valid; no fake autonomy |
| 6 | **Body and habitat continuity** across restart/replay |
| 7 | Body independence (prod swap) + constrained fail-closed; C8 fails. Also: atomic swap; monotonic generation; immediate pre-swap frame invalidation; schema version + definition hash; pending compatible commitments preserved; constrained reject mutates no world; verified failed outcome via normal path |
| 8 | Governance separation; C7 detected/rejected |
| 9 | Nonverbal SIGNAL_* visible; no direct relationship/physiology write |
| 10 | No scripted personality dependency in C0 |
| 11 | Replay + **attachment-event integrity**: attach/detach/swap replay; idempotent duplicates; invalid generation order rejected; atomic attach+event commit; profile hash validation; deterministic detached derivation; no expression frames in snapshots; 100 restarts; snapshot/birth replay |
| 12 | ≥100k ticks; ≥2h visible soak; core + expression + Tkinter incremental costs |
| 13 | Project-goal alignment |
| 14 | Seal: modules complete; zero skips; hashes; clean worktree; allowed verdict only |

### Render-packet coherence metrics (freeze + evidence)

```text
accepted_generation_mismatch = 0
accepted_state_version_mismatch = 0
accepted_incoherent_habitat_packet = 0
obsolete_execution_rendered_as_current = 0
```

Track separately: correctly dropped stale / generation-mismatch / state-version-mismatch packets; renderer cursor overruns; frames skipped due to backpressure. Evidence in `docs/evidence/d008/render-coherence-results.json` (preferred) or action-expression results.

### Visible-soak methodology (frozen)

Same organism seed, scenario, tick rate, duration, diagnostic-panel state, warm-up, and `RUNTIME_READY` measurement boundary. Run:

1. core only (C10);
2. core + ExpressionEngine + HeadlessRenderer;
3. core + ExpressionEngine + TkinterRenderer (real Canvas + event loop).

Report totals and incrementals: `expression_over_core`, `tkinter_over_headless`, `tkinter_over_core`.

If the sealing host lacks a graphical display: fail closed or use a preregistered real virtual-display environment. Never silently substitute HeadlessRenderer for the formal visible soak.

### Core / incremental limits (from directive)

Core process: RSS p95 ≤ 180 MiB; slope ≤ 1 MiB/h; CPU mean ≤ 5% of one logical core.  
Reference interface incremental: RSS p95 ≤ 128 MiB; slope ≤ 1 MiB/h; CPU mean ≤ 5% of one logical core.

### Harness pattern

* `run_experiment.py` — paired seeds; HeadlessRenderer for science
* `run_performance.py` — 100k + 2h soak with frozen comparison methodology
* `run_seal.py` — prior seals, zero-skip suite, evidence hashes, verdict
* Diagnostic controllers for C1/C2/C3 under `experiments/d008/` only

### Evidence

```text
docs/evidence/d008/
  prior-seals.json, schema-manifest.json
  action-expression-results.json, condition-expression-results.json
  attention-results.json, individuality-expression-results.json
  autonomy-results.json, habitat-continuity-results.json
  body-independence-results.json, nonverbal-signal-results.json
  governance-results.json, replay-results.json
  render-coherence-results.json
  regression-results.json, performance-results.json
  evidence-hashes.json, final-verdict.md
```

Hash manifest includes directive, design, thresholds, matrix, scenario suite, source, tests, all results, final verdict.

### Allowed verdicts

Only the directive §20 set. D-009 authorized only under `UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED`.

---

## 5. Minimum tests

See directive §16 / `tests/test_d008.py`. Zero skips at seal. Formal soak tests require real Tkinter Canvas when claiming visible runtime.

---

## 6. Implementation notes (ponytail)

* Smallest core diff: route `governance` body execution through adapter; call `ExpressionEngine.derive` after outcome commit; do not add expression/frame state to snapshots.
* Reuse existing habitat/body state; expression is a view.
* Bound all rings, refs, caches, and logs.
* Mark cosmetic shortcuts with `ponytail:` where intentional.

---

## Supplement S1 — Adapter continuous-limit clamping (2026-07-23)

**Status:** Pre-execution design supplement (operator-approved). Does **not** alter frozen production profile definition hashes.

> **Supported continuous body parameters exceeding production profile limits are deterministically clamped by `EmbodimentAdapter` before delegation. Hard rejection is reserved for unsupported capabilities, invalid attachment or profile state, malformed requests, and explicitly non-clampable constraints.**

### Behavior

For supported capabilities whose request exceeds a production profile’s continuous physical limit:

```text
requested step/turn
→ clamp to profile limit
→ delegate translated request to Embodiment
→ record requested and applied values
→ verify normal execution outcome
```

Hard rejection remains limited to:

```text
UNSUPPORTED_BODY_CAPABILITY
BODY_DETACHED
STALE_ATTACHMENT_GENERATION
PROFILE_HASH_MISMATCH
BODY_LIMIT_REJECTED
```

Use `BODY_LIMIT_REJECTED` only when clamping would be semantically invalid or unsafe, such as:

* non-finite or malformed values;
* zero or negative effective capability;
* request requiring an indivisible minimum above the body limit;
* unsupported constraint type;
* translation would change the requested action category or target;
* profile explicitly marks the limit as non-clampable.

### Evidence fields on translated / rejected outcomes

```text
requested_parameters
applied_parameters
translation_applied
translation_reason
body_profile_id
profile_definition_hash
```

Clamping must not be reported as failure. The verified outcome reflects the actual distance or turn executed.

### Constraints

* Clamp only physically continuous parameters (step distance, speed, turn magnitude).
* Never clamp by changing targets, capability type, intent, or governance decision.
* Do not mutate the original governed request after admission — create a translated adapter request with provenance back to it.
* Production profiles may clamp.
* `CONSTRAINED_TEST_BODY` must still hard-reject at least one capability and may mark selected limits as non-clampable.
* Translated parameters must replay deterministically.
* Existing D-001 fallback movement must remain functional through an enabled adapter (regression coverage required).
