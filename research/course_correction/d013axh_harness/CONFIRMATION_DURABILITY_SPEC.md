# Confirmation durability

Every synthetic preliminary rescue creates a deterministic confirmation ID from
the protocol fingerprint, source logical branch, and horizon. Confirmation
rows use `PENDING`, `RUNNING`, `COMPLETE`, and `FAILED` states and retain their
source branch and result hash. A terminal summary requires all confirmations
to be complete.
