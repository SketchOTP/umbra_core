# UMBRA-AS-003C result

Verdict: `AS003C_DOMINANCE_NOT_REALIZED`

AS-003C froze exactly once at `e336c25064dd87b7a71966f034ba317fa7cb6116`. The Architect-authorized migration replaced only the obsolete scalar-winner replay assertion; frozen retained replay passed `58/58`. Diagnostic A completed `500/500` and Diagnostic B `3500/3500` without a critical failure or `NO_SAFE_ACTION`.

The mechanism gate fails: 2,647 qualifying ordinary multi-candidate decisions produced zero supported-dominance eliminations, and all 2,647 retained the full frontier. Secondary observation: `AS003C_FRONTIER_SATURATION_FAIL`. No later frozen stage ran. Post-freeze production/test changes, remediation, retry, reseed, known R1, fresh population, AS-004, and CLOSE-03: 0.

Final evidence manifest: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003c-replay-migration-qualification-r1/AS003C_EVIDENCE_MANIFEST.json`; SHA-256 `d8eb4cc26048f6b3b8d9ca861dbfab25f56a6e2b95548949997c638f7812268c`.
