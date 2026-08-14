# Search lifecycle

States are `DRAFT`, `FROZEN`, `RUNNING`, `CLOSED`, and `INVALIDATED`. Once frozen/running, evaluator, partitions, and allowlist cannot change. Once closed, no candidate may be added under the same run ID. CC-6 does not perform a search or optimization.
