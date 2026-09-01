# AS-003K evidence protocol

The evidence root is durable Atlas storage. Artifacts are written by an offline analysis helper using temporary-file write, file fsync, atomic rename, directory fsync, SHA-256 readback, and a final manifest. The helper reads static source/evidence metadata and evaluates only embedded synthetic matrices; it imports no UMBRA runtime code and cannot construct or tick an organism.

Prohibited execution: organism/runtime construction, tick methods, embodiment, persistence mutation, learning, organism RNG, diagnostics, and broad pytest.
