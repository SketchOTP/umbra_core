# Evaluator restart continuity

V2 evaluator rows are append-only trace records containing the full normalized
trace row plus execution, directive, baseline, configuration, contract, and
fingerprint identity. A replacement worker reconstructs
`recovery_episode_rows` from that trace.

This is harness state only. It is not written into organism memory or treated
as organism lived experience.

Result: continuity across worker generations passed as `NON_FORMAL_TEST`.
