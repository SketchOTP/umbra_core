# UMBRA-G-001C closeout

- Starting commit: `95e43c9e5c097ff1bf53308a059b8bee0e01dfda`
- D-010 diagnostic-only commit: `9e313f1529a0b5992c878c3781715d75e2c671e1`
- G-001 governance commit: `7c34d99b2594765e8b92ce650a6b5c9918ceb475`
- Final repository tip: the closeout commit containing this record.
- Final worktree status: clean after this closeout commit.
- Classification ledger SHA-256: `6f6edde72e9d5e94c61ad2bed32a856a4f01ad3019e42b67f1b627b1f7e543e5`
- Clarified goal SHA-256: `b6db14fa8adf8134f537d614d4befac97b28f6e4a3069b1de66a4878fef3588b`
- D-009 seal: `af35371`
- D-010 verdict: `UMBRA_D010_PERFORMANCE_FAIL`

The D-010-R1 commit is diagnostic-only. Its P0 reconfirmation failed and it does not create Stage B v7, a qualified release, or a successor to D-009. No D-010 frozen thresholds, matrix, scenario suite, or performance protocol changed. D-001 through D-009 evidence and `.agent/RECORD.md` remain unchanged.

Validation: `python tools/validate_governance.py` passed; `pytest -q` passed (651 passed, 2 documented Tkinter-dependent skips); `git diff --check` passed; no experiment or soak process remained active.

Verdict: `UMBRA_G001_GOAL_AUTHORITY_RESTORED`.
