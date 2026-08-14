# V2 evaluator initialization

The campaign runner writes exactly one `EVALUATOR_INIT` JSONL record before
launching a worker. It uses the existing append/flush/fsync JSONL mechanism
and carries directive, formal execution ID, starting commit, configuration
fingerprint, verdict namespace, contract version, and contract fingerprint.

The record contains no recovery proposal, physiology event, outcome, or
episode payload. A worker accepts one valid init record, rejects duplicates or
conflicting identity, and does not add init to `recovery_episode_rows`.
