# SIGTERM versus SIGKILL

Both paths terminated a distinct worker during `RUN_DIAGNOSTIC_TICKS`. SIGTERM invokes the normal operating-system termination path, but the worker has no custom SIGTERM handler, so Python cleanup is not guaranteed. SIGKILL bypasses cleanup entirely.

Before correction, SIGTERM could leave a committed event row without the matching ledger-tip metadata update. SIGKILL did not reproduce that state in the bounded comparison. Ownership reclaim remained identity-safe: generation 2 used `reclaim_dead=True`, created a stale owner record, incremented ownership generation, and did not steal a live owner.
