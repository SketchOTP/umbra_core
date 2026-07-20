# DIRECTIVES.md

Append-only task-start log for UMBRA-CORE. Never rewrite, reorder, or delete history.

Format:
```md
- D-YYYYMMDD-HHMM-slug | status:started | scope:<files/modules> | ask:<one sentence> | accept:<observable done condition> | plan:<max 3 tiny steps>
```

- D-20260720-0937-umbra-rule-conversion | status:started | scope:.agent/*,AGENTS.md,COMMANDMENTS_OF_THE_CODE.md,.cursor/rules/*,.cursor/skills/mimir,.cursor/mcp.json | ask:Convert all copied AI-coder rule files to UMBRA-CORE using PROJECT_GOAL as basis | accept:No foreign-repo residue in rules/profile/map/memory; PROJECT_GOAL unchanged; greenfield map matches filesystem | plan:rewrite profile+map+memory, convert rules+AGENTS, validate with rg
- D-20260720-0942-umbra-d000-prior-art | project:UMBRA-D-000 | status:started | scope:docs/directives/UMBRA-D-000*,docs/prior-art/*,.agent/PROJECT_PROFILE.md,.agent/REPO_MAP.md,AGENTS.md,.cursor/rules/04*,.cursor/rules/05* | ask:Insert UMBRA-D-000 prior-art reproduction gate before D-001; correct blind-greenfield stance | accept:D-000 directive+ledger+gates landed; D-001 blocked in profile/map/rules/AGENTS; PROJECT_GOAL unchanged | plan:write D-000+ledger, update profile/map/rules, close local memory
