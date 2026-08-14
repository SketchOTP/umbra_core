# Execution Segment Contract

CC-3 uses one execution with multiple segments, not a parent/child execution
model. The pre and post segment IDs are distinct, but their execution ID,
definition fingerprint, seed, database identity, and identity commitment must
match. The validator rejects unrelated databases, seeds, scenarios,
conditions, organisms, or evidence. Segment order is `pre` then `post`; the
post segment must finish the declared budget.
