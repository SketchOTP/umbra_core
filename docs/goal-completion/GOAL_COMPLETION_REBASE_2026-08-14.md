# UMBRA Goal Completion Rebase — 2026-08-14

## Scope and authority

This is a documentation-only rebase against `.agent/PROJECT_GOAL.md` at
repository HEAD `c3153dd0ba2584bb9e505ea51af5ee040b0f56f2`. It does not reopen
CC-1 through CC-6R3, change production code, regenerate experiments, authorize
ASAL or an optimizer, or qualify any failed stage.

The matrix uses these meanings:

- `QUALIFIED`: the named capability has a surviving formal qualification and seal.
- `IMPLEMENTED_BUT_UNQUALIFIED`: mechanism/evidence exists, but the required qualification boundary failed or remains open.
- `PARTIAL`: important subsystem evidence exists, but the end-goal capability is not demonstrated end-to-end.
- `FAILED`: the current integrated claim has a preserved negative result.
- `NOT_TESTED`: no meaningful end-goal validation exists.

The percentage below is planning coverage, not a scientific qualification score:
`QUALIFIED = 1`, `IMPLEMENTED_BUT_UNQUALIFIED = 0.5`, `PARTIAL = 0.25`, and
all other states = 0.

## Current completion matrix

| Goal capability | Status | Strongest existing evidence | Current blocker / evidence boundary | Blocker class | External check before new implementation | Minimum next experiment | Dependency |
|---|---|---|---|---|---|---|---|
| Persistent self | `PARTIAL` | D-001 invariant companion core; D-009 persistence/replay seals | Restart/migration/body-transfer identity continuity is not qualified as one organism-level claim | integration | Yes | Cross-version restart plus compatible-body migration identity replay | D-010/D-012 continuity boundaries |
| Autonomous continuity | `PARTIAL` | D-009 autonomous habitat operation and adaptive soak | Integrated D-012 organism stopped at the viability floor | integration/performance | Yes | Prompt-free integrated P0 viability run after authorized correction | D-012 |
| Causal behavior | `PARTIAL` | D-001–D-009 governed subsystem mechanisms and verified outcomes | End-to-end causal behavior across all subsystems has not survived an integrated long run | integration | Yes | Integrated causal trace with outcome-to-learning audit | D-012 |
| History-dependent individuality | `QUALIFIED` | D-007 `UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED` | No remaining subsystem blocker identified; integrated long-horizon coupling remains open | integration | No new mechanism; check only if extending scope | Multi-history integrated confirmation | D-012 |
| Selective memory | `QUALIFIED` | D-005 `UMBRA_D005_MEMORY_CONSOLIDATION_QUALIFIED` | End-to-end long-horizon coupling remains unproven | integration | No new mechanism; check before redesign | Integrated memory-consequence replay | D-012 |
| Relationship formation | `QUALIFIED` | D-006 `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED` | Months-scale relationship persistence is not demonstrated | experiential/integration | Yes before new social mechanism | Multi-history partner-contingency continuation | D-012 |
| Development | `QUALIFIED` | D-004 `UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED` | Long-horizon autonomous development remains unproven | integration | Yes before new mechanism | Development across an uninterrupted bounded life run | D-012 |
| Embodied self-model | `PARTIAL` | D-002 self-model qualification and D-008 coherent embodiment qualification | Body change and transfer continuity are not qualified together with identity/history | integration | Yes | Compatible-body transfer with causal self-model continuity | D-010/D-012 |
| Persistent environmental agency | `QUALIFIED` | D-009 `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED` | Integrated organism viability and long horizon remain open | integration | No infrastructure expansion | Reconfirm only as part of integrated life | D-012 |
| Temporal continuity | `IMPLEMENTED_BUT_UNQUALIFIED` | D-010 Gates 0–12 pass; restart, replay, recurrence, downtime, and anticipation evidence exist | Gate 13 adaptive performance failed; D-010 remains `UMBRA_D010_PERFORMANCE_FAIL` | performance | Yes before any new temporal mechanism | Separately authorized D-010 performance-boundary revalidation | D-010 |
| Expression integrity | `QUALIFIED` | D-008 `UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED` | Believable-creature experience is not thereby established | experiential | No new renderer architecture | Observe expression during integrated life evidence | D-012 |
| Body/interface independence | `PARTIAL` | D-008 embodiment adapters and D-011 governed perception adapters | Removal/replaceability across a complete living organism is not end-to-end qualified | integration | Yes | Run core with body/interface variants and no language controller | D-012 |
| Restart/downtime continuity | `PARTIAL` | CC-3 research contract and D-010 restart/downtime evidence | Contract evidence is supporting infrastructure; organism-level long-horizon continuity remains unqualified | integration | No new harness; reuse existing contract | Integrated restart after bounded autonomous interval | D-010/D-012 |
| Body-transfer continuity | `PARTIAL` | Body-profile/adapter boundaries and body-independent architecture | No qualified identity/history transfer campaign across compatible bodies | integration | Yes | One preregistered compatible-body transfer continuity experiment | D-012 |
| Essential-system ablation | `NOT_TESTED` | Existing subsystem qualifications and controls | No completion-level ablation showing removal of memory, relationships, self-model, world model, individuality, temporal continuity, or history causes measurable loss | scientific | Yes, before designing ablation | Preregistered essential-organization ablation matrix | D-010/D-012 status must be explicit |
| Long-horizon continuous life | `FAILED` | D-010 performance failure; D-012B2 P0 integrity failure at tick 181 / energy 0.0485 | No days-scale continuous-life qualification; integrated viability is currently false | performance/integration | Yes | Multi-day bounded continuous-life run after P0 viability is restored | D-012, with D-010 performance boundary |
| Integrated organism viability | `FAILED` | D-012B2 formal P0: energy crossed below 0.05 at tick 181; no complete positive-energy recovery cycles | Formal P0 stopped fail-fast; P1/P2/D-012C and relaunch remain unauthorized | scientific/integration | Yes | Evidence-first D-012 P0 viability revalidation after separately authorized correction | D-012 |
| Believable-creature outcome | `NOT_TESTED` | Project goal and qualified subsystem foundations | No observer-level validation of persistent, unscripted, history-shaped creature experience | experiential | Yes | Behavioral/observer validation after organism gates pass | D-010/D-012 and all core capabilities |

### Planning coverage

`6` qualified + `1 × 0.5` implemented-but-unqualified + `7 × 0.25`
partial = `8.25 / 18`, or approximately **46% planning coverage**.

This number must not be represented as “46% scientifically qualified.” The
remaining half is dominated by integration, temporal performance, viability,
long-horizon, ablation, and experiential gaps.

## Unresolved goal-critical blockers, ranked

1. **Integrated viability failure (D-012B2).** The organism crossed the energy
   floor and never completed a positive-energy recovery cycle. This is the most
   direct blocker to a living companion claim.
2. **Temporal performance boundary (D-010).** Functional temporal gates passed,
   but Gate 13 failed, so temporal continuity is not qualified.
3. **Long-horizon life.** Days/months/years-scale continuity and bounded resource
   behavior remain unproven, and cannot be meaningfully tested before viability.
4. **Essential-organization ablation.** The project has not demonstrated that
   removing core organization materially damages the organism.
5. **Body-transfer continuity.** Architecture supports body independence, but
   identity/history preservation across compatible bodies lacks an end-to-end
   qualification campaign.
6. **Believable-creature validation.** The target lived experience has not yet
   been evaluated as an organism-level outcome.

## Single recommended next scientific action

**When separately authorized, perform one evidence-first D-012 integrated P0
viability revalidation focused on the preserved energy/recovery failure, with
the D-010 performance boundary declared as an explicit dependency.**

Do not start it under this rebase. First freeze the exact correction and
preregister the minimum viability gates: no energy-floor crossing, at least
one complete positive-energy recovery cycle, fail-closed behavior, preserved
identity/history, and unchanged prior evidence. Only after that passes should
long-horizon life, ablation, or observer validation be considered.

This action moves UMBRA closest to the companion-organism goal because it tests
whether the integrated organism can remain alive and self-regulating at all.
The discovery firewall remains preserved as research infrastructure, but it is
not a current completion criterion and no further CC-6 remediation is proposed.

## Governance conclusion

`CC6_DISCOVERY_FIREWALL_RESEARCH_PROTOTYPE_DEFERRED`

The CC-6R3 prototype is strong enough to preserve as research-only supporting
infrastructure, but automated discovery remains unauthorized. Governance
protects the science; it is not the science.
