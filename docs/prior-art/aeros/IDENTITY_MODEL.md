# Identity model

## AEROS

- `PersonaCore` (frozen) enters identity hash — includes **risk_appetite, verbosity, human_check, value_ordering**, soak policy.
- `PersonaAdaptive` stays outside identity hash (skill_confidence, tendencies).
- Identity hash stability across capability/model changes is a design goal with source+tests.

## UMBRA independent contract

Constitutional fields only: `agent_id`, `lineage_id`, `birth_event_id`, schema version, `operator_authority_root`, `lifecycle_sequence`, `identity_commitment`, `created_at`.

**Excluded:** mood, preferences, memories, Big Five, appearance, language style, current model/body/skills.

## Classification

- Split frozen vs adaptive: **REFERENCE** (useful axis) / clean-room **ADAPT** for constitutional vs developed.
- Persona traits inside identity hash: **REJECT** for UMBRA constitutional identity.
