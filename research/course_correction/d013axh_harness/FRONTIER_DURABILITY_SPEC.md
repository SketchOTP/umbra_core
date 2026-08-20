# Frontier durability

`COMPLETE, expanded=0` is the durable parent state requiring frontier
expansion. Child rows and `frontier` edges are inserted transactionally before
the parent becomes `expanded=1`. A crash rolls back the transaction; a restart
repeats deterministic expansion idempotently. No parent-only frontier state is
authoritative.
