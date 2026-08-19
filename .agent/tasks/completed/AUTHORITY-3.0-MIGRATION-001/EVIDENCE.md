# AUTHORITY-3.0-MIGRATION-001 — Evidence

## Baseline
- Branch: `master`
- Local/remote baseline: `3e0aa896a2acf30733282b276f3f518ca82c18f4`
- Pre-existing untracked file: `.agent/LIBRARY_REVIEW.md`

## Canonical source
- Authority 3.0 Notion package: https://app.notion.com/p/3bf833cb27ff811aae15def88959797e
- Retrieved: 2026-08-19
- Disposition: ADOPT

## Preserved hashes
- Pre-migration `.agent/CURRENT.md`: `cbe46686f0a99785d166e6868be3632d5d69eb8ab0ef75e0ddc4bc4659a37b82`
- Pre-migration `.agent/PROJECT_PROFILE.md`: `8d0d7eb8481024134f9cd958db8a6ae9ab2e2301937e966e815227089f5a970c`
- Pre-migration `.agent/REPO_MAP.md`: `4830d3e8b2782dc84daab8ce4aadf3f69a5bd1dc667f463e0f261abff7838cdc`
- Pre-migration `.agents/skills/external-discovery/SKILL.md`: `07b74825d47d07b56bd373974b0e949aa3b743142b67b02bbe6378379125fe0c`
- `.agent/PROJECT_GOAL.md`: `325af18327f4f2d36812972033a1671a36a5b1546d78deac26041614460d8ac7`
- `.agent/RECORD.md` before authorized append: `a0d61b22f3fce8a6014493c7e8685aa0f930e7ad2fa48a1e9d51fa57b3bd4f23`
- `.agent/LIBRARY_REVIEW.md`: `35f303ff28dfdf296308a3692b71019da77187fa08d868808a05efe35237c345`

## Validation
- `python3 scripts/validate_authority_v3.py`: PASSED; schema 3.0, seven active reusable files, nine preserved legacy artifacts.
- `python3 scripts/validate_governance.py --mode ADOPTED`: PASSED; legacy mode accepted as compatibility alias.
- `python3 scripts/test_validate_governance.py`: PASSED; clean positive fixture plus four fail-closed negative fixtures.
- `python3 -m pytest -q tests/test_governance_validation.py`: PASSED; 9 tests.
- D-009 evidence validator: PASSED; 14 files, 3,300 raw rows.
- D-010 evidence validator: PASSED; 1,900 raw rows.
- Full suite: 854 PASSED, 2 SKIPPED, 1 FAILED. The failure is the unchanged D-010 runtime-tick inventory test with the inherited 27-entry footprint.
- `git diff --check`: PASSED.
- Production/experiment/scientific-evidence diff: NONE.
- `.agent/PROJECT_GOAL.md` preserved SHA-256: `325af18327f4f2d36812972033a1671a36a5b1546d78deac26041614460d8ac7`.
- `.agent/LIBRARY_REVIEW.md` preserved SHA-256: `35f303ff28dfdf296308a3692b71019da77187fa08d868808a05efe35237c345`.

## Evidence level
`E4_REGRESSION_PROTECTED`: targeted deterministic governance validation passes and the broader suite confirms no new failure beyond the unchanged D-010 inventory defect.
