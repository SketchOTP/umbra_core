# REPO-001 post-surface audit

## Verdict

The repository now has an independently understandable public front door. A first-time
reviewer can identify the product goal, non-goals, authority path, bounded scientific
claims, important failures, current research frontier, and evidence routes without
reading private session history or starting in internal agent directories.

## Reviewer questions

1. **Can a first-time reviewer understand the project without chat history? — Yes.**
   The root README opens with a plain technical definition, motivation, and explicit
   non-goals, then routes to implementation and durable evidence.
2. **Is the current scientific status obvious? — Yes.** The claim-status table uses
   bounded labels and states that integrated long-horizon viability is not qualified.
3. **Are qualified and unqualified claims separated? — Yes.** Qualified subsystem
   lineages, bounded AS-003S evidence, failed action-selection work, and active research
   questions are presented separately.
4. **Are important failures visible? — Yes.** The selected-negative-results section
   preserves historical viability, action-selection, and observer-measurement failures.
5. **Can a technical reviewer find architecture and evidence? — Yes.** The architecture
   diagram, repository map, README links, and `docs/EVIDENCE_GUIDE.md` provide direct
   routes to source, result packets, and governance state.
6. **Can a hiring reviewer identify engineering depth? — Yes.** The front door exposes
   persistent-state architecture, authority separation, evidence discipline, crash-safe
   body replacement, and explicit failure handling without résumé-style claims.
7. **Does internal tooling still dominate the presentation? — No at the landing page.**
   Internal directories remain visible in the tree by design, but the rendered README is
   now the primary GitHub landing surface and explains their role.
8. **Are there broken or stale public-document links? — No broken relative links found.**
   Static validation checked 82 README/evidence-guide links; live GitHub rendering also
   confirmed the evidence-guide link and Mermaid container.
9. **Does the repository feel intentionally maintained? — Yes.** The status vocabulary,
   evidence map, qualified boundaries, validation transparency, and current frontier are
   explicit and internally consistent.
10. **What presentation debt remains? — Bounded and visible.** See below.

## Before / after

Before REPO-001, the authoritative branch had no root README and GitHub's public default
branch pointed to an unrelated stale `main`, so the landing page did not expose the
project. After REPO-001, authoritative `master` is the default branch and renders the
new README, architecture diagram, status tables, and evidence navigation. The stale
branch was preserved; no history was rewritten or deleted.

## Remaining presentation debt

- Authoritative `master` has no root license file; the README states this rather than
  implying reuse rights.
- There is no single package/install contract (`pyproject.toml`, lock file, or root
  requirements file), so local-use instructions intentionally assume an already
  compatible Python/pytest environment.
- The large frozen D000S architecture dossier is historically valuable but can lag live
  implementation; the evidence guide labels that boundary and routes current claims to
  source/result packets.
- GitHub About metadata, contribution policy, security policy, and formal releases remain
  absent. They were outside this directive.
- The unrelated historical `main` branch remains preserved but is no longer the default.

## Scope and integrity

- Production delta: `0`
- Existing test delta: `0`
- Experiment delta: `0`
- Scientific evidence rewrite: `0`
- Organism creations/ticks: `0/0`
- Diagnostics/qualifications: `0/0`
- Retries/reseeds: `0/0`
- Successor started: `no`
