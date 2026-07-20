# License audit (engineering assessment — not legal advice)

## Default

`aeros-core` repository default: **AGPL-3.0-or-later**.

## NOTICE claim

NOTICE asserts Apache-2.0 for integration surfaces:

- `src/aeros/interfaces.py`
- `src/aeros/providers/`
- `src/aeros/mcp/`
- `bridge/schemas/`
- `ecm_library/`
- `openclaw-plugin/`

Each carries a LICENSE or SPDX header. **Directory placement alone does not prove separability** for derivative works of AGPL core.

## Rules applied

| Status | Meaning |
|---|---|
| PERMISSIVE_REUSE_CANDIDATE | Apache surface; file-level confirm before any copy |
| AGPL_REFERENCE_ONLY | Read/measure only; no copy into UMBRA product |
| CLEAN_ROOM_REIMPLEMENTATION_REQUIRED | Mechanism useful; reimplement independently |
| LICENSE_AMBIGUOUS | Do not copy |
| REJECT | Do not use |

## UMBRA policy

- Do **not** depend on AGPL aeros runtime in production packages.
- Do **not** translate AGPL source line-by-line.
- Concepts, papers, public interfaces, measured behavior may inform clean-room design.
- Ambiguity → no code reuse.

See `docs/evidence/d000-track4/license-manifest.json`.
