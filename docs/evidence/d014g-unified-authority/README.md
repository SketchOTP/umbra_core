# D-014G  Unified Candidate Proposal / Single Final Selection Authority

Status: active, non-formal, shadow-first.

Baseline: c198b46413731444222e8e1fa8495d932f2aa836

Permanent evidence root:

/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014g-unified-authority-r1/

Initial evidence:

- D014G_AUTHORITY_TOPOLOGY.json
- D014G_PROPOSAL_POOL_CONTRACT.md
- D014G_TRANSLATION_SHADOW_RESULTS.json

Phase A finding:

The runtime calls Arbitrator.select() at umbra_core/runtime.py:1349, then
mutates the candidate before Governance.propose() at runtime.py:1603 through
development practice, memory retrieval, social proposal, world-model planning,
dormant-capability narrowing, and final safety narrowing. The read-only
translation shadow reproduced the observed final candidate for 16 comparisons
across 32 bounded ticks with zero mismatches.

Boundary:

The D-014F RegulatoryOpportunity mechanism is a frozen external shadow
specification, not an implementation in umbra_core. No D-014F opportunity
generator or executable proposal source was found in the repository. Related
D-013AO recoverability view/contracts are not silently promoted into D-014F
behavior. Production changes remain conditional on the D-014G shadow gates.

Protected state and scientific source remain unchanged.
