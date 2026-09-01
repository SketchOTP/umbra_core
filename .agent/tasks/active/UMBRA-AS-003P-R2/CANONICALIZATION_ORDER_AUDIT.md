# AS003PR2 Canonicalization Order Audit

## Frozen procedure

The frozen `_semantic_runtime_value()` recursively sorts dictionary entries by
the raw string form of each key, emits each raw key unchanged, and only then
replaces UUID-looking strings encountered in values with first-occurrence
tokens. It therefore has two independent defects for generated-ID owner maps:

1. UUID dictionary keys are never abstracted at all, so a pure bijective
   administrative-ID rename necessarily compares unequal.
2. Raw UUID lexical order determines value traversal. First-occurrence tokens
   can consequently bind to different semantic records across independently
   generated but structurally equal maps.

The preregistered synthetic proof contains four false positives and no false
negatives across its eight required cases. UUID-key ordering is causal to the
frozen comparator's behavior.

## Independently justified alternatives for future analysis

### Owner-provided comparable state

Use an owner-specific structural representation where one already exists and
its exclusions are documented. `WorldModel.accepted_state()` is evidence for
this approach, but it is intentionally narrower than observer parity and
cannot alone prove that excluded histories, metrics, timing, or relationships
are equal.

### Semantic multiset for ID-keyed owner collections

When a map key is solely the administrative identity of a self-contained
record, compare the records as a semantic multiset after removing only that
owner-proven administrative key and the duplicate identity field. This is
sound for the retained active WorldModel model map because all behavioral
model fields are compared exactly and model identity is separately audited as
provenance rather than merit.

### Identity abstraction before semantic ordering

For structures whose identities are referenced elsewhere, first construct a
bijective identity graph, then order nodes from semantic labels and relation
structure. Replacing values after raw-key sorting is not sufficient.

### Canonical graph labeling

For predictions, contradictions, supersessions, or other relationship-bearing
records, canonicalize nodes from exact semantic content plus edge structure.
This preserves aliasing and relationship meaning while remaining invariant to
administrative renaming. It is more complex and should be used only where an
owner-specific projection cannot express the required equality.

## R1 boundary

No alternative was selected because it makes R1 pass. The retained comparison
uses the Architect-locked field contract, exact numerical values, the existing
owner `accepted_state()` rationale, and separate relationship/history checks.
R1's historical frozen-comparator verdict remains unchanged.
