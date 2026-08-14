# Fault-injection results

Status: `PASS`, 11/11 detected, 0 silent failures.

Detected and rejected: condition mutation, wrong seed, wrong execution ID, tick-budget truncation,
wrong execution path, metric substitution, aggregation corruption, control
contamination, stale frozen configuration, evidence-path contamination, and
verdict/evidence mismatch. Each fault was inserted into a research-only
contract record. None could become a valid-looking result.
