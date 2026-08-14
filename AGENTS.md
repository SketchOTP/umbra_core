# Authority Repository Instructions

Codex is the primary coding agent. This file is the always-on router; detailed rules live in the referenced governance files and skills. Codex skills live under `.agents/skills/`.

## Mandatory preflight

Before planning, editing, or validating work, read the complete `.agent/` contract:

- `.agent/PROJECT_GOAL.md`
- `.agent/PROJECT_PROFILE.md`
- `.agent/CURRENT.md`
- `.agent/DIRECTIVES.md`
- `.agent/OUTCOMES.md`
- `.agent/LEARNINGS.md`
- `.agent/RECORD.md`
- `.agent/REPO_MAP.md`

These files are authoritative and consumed by multiple processes. Reading or validating them must not alter their data. Do not rewrite, reorder, reformat, truncate, replace, or selectively ignore them. Change them only when the user explicitly authorizes a project-state or governance update, while preserving their append-only rules.

## Detailed guidance

- Precedence, scope, safety, lifecycle, validation, and reporting: `COMMANDMENTS_OF_THE_CODE.md` and the `.agent/` contract.
- Codex governance workflow: `.agents/skills/authority-governance/SKILL.md`.
- External prior-art discovery: `.agents/skills/external-discovery/SKILL.md` when the task meets that skill’s activation conditions.
- Mimir workflow: `.cursor/skills/mimir/SKILL.md` only when Mimir is configured and applicable.
- Cursor rules and Claude/Gemini files are compatibility adapters; they must defer to this file.

## Operating requirements

Preserve existing qualified work and project-specific instructions. Inspect existing implementations and tests before substantial changes. Search for external prior art before building significant new capabilities. Validate proportionally, record outcomes in `.agent/OUTCOMES.md`, update `.agent/CURRENT.md`, and report failed, unavailable, skipped, and unrun checks honestly.

Nested `AGENTS.md` files may add scoped guidance. They must preserve this mandatory `.agent/` preflight and may not silently replace the repository contract.
