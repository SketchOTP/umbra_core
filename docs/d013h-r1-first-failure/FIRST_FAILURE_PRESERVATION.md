# First-failure preservation

Closeout now treats evidence publication as a later lifecycle stage. If a
scientific failure such as `organism_identity_changed` already exists, a
subsequent publication failure is stored separately under
`secondary_evidence_failures`; it cannot replace the primary invariant.

If no scientific failure exists, a publication failure becomes the terminal
fail-closed integrity result. Both cases are covered by focused tests.
