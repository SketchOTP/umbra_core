# Limitations

- Upstream embedding sidecar not available; memory writes required SQL mock.
- Upstream pytest not executed (asyncpg and full deps not installed).
- Full consent/character init and LLM heartbeat worker path not run.
- Apache AGE behaviors not load-tested.
- Independent reproduction is contractual, not a byte-for-byte Hexis clone.
- 100 worker restarts tested via SQLite reconnects; Hexis worker containers not looped 100×.
