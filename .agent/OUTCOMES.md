# OUTCOMES.md

Append-only task-end log for UMBRA-CORE. Never rewrite, reorder, or delete history.

Format:
```md
- D-YYYYMMDD-HHMM-slug | status:done|partial|blocked | files:<changed files> | tests:<cmd/result or not run + why> | accept:<met|partial|not met> | summary:<one sentence> | next:<optional>
```

- D-20260720-0937-umbra-rule-conversion | status:done | files:.agent/* (except PROJECT_GOAL),AGENTS.md,COMMANDMENTS_OF_THE_CODE.md,.cursor/rules/*,.cursor/skills/mimir/SKILL.md,.cursor/mcp.json; deleted .cocoindex_code,04-cocoindex,05-animus | tests:rg foreign-residue CLEAN; PROJECT_GOAL unchanged | accept:met | summary:Retargeted all AI-coder rules/memory from digital_cell/hermes copies to greenfield UMBRA-CORE on PROJECT_GOAL | next:bind Mimir when register works on this checkout
- D-20260720-0942-umbra-d000-prior-art | project:UMBRA-D-000 | status:done | files:docs/directives/UMBRA-D-000-prior-art-reproduction.md,docs/prior-art/*,.agent/PROJECT_PROFILE.md,.agent/REPO_MAP.md,AGENTS.md,.cursor/rules/04-umbra-architecture.mdc,.cursor/rules/05-project-directives.mdc | tests:D000_OK; PROJECT_GOAL md5 unchanged; gate language in AGENTS/profile/rules | accept:met | summary:Landed UMBRA-D-000 prior-art gate blocking D-001; corrected blind-greenfield stance to informed reuse | next:execute D-000 reproduction tracks; operator append RECORD
