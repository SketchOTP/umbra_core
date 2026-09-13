# UMBRA-AS-017 integrated-core closure readiness

Status: PRE-LOCK DEVELOPMENT. This record does not authorize a scientific
lock, formal organisms, or formal seed consumption.

## Subject and boundaries

- Development baseline: `f9bb1f809602b584b4931d887115d252d164e5e2`
- Published master at adoption: `fd8c50e1134d7d2ef54e20148ac9b7880e63708d`
- V5 predecessor subject: `fe783295a0de175b88000a9ffadfd1b7ff4afa38`
- Formal seeds consumed: `0`
- Historical V5/V1--V4C evidence: preserved and not pooled with this subject.

## Implemented closure

The candidate now uses one pure physiology transition projection for
effect-clamp followed by drift-clamp, including the existing state-dependent
locomotion rules owned by Governance. Arbitration and recovery assessment pass
explicit successor context rather than consulting live root state. The
historical prospective-recoverability API was restored for the orphan import,
and stale tests for a removed arbitration hook were modernized against current
authority behavior. The AS-015 literal preflight accepts a unique create-once
publication name so an old artifact cannot mask a new run.

## Validation

Focused closure command, run twice:

- `382 passed` in `45.02s`; CPJ result log SHA-256
  `298f9c37a8065bcc1dbda3b8c232127341860182c97039032960e56940dbfc2f`
- `382 passed` in `46.34s`; CPJ result log SHA-256
  `d8610b0123665ef17c44309f8a770d049dc394d09a34f60f4a016ef2b999f0d8`

Full repository regression after the repair:

- `1383 passed / 4 skipped / 7 failed`
- CPJ result log SHA-256
  `772b5b56dc131c1a805b5e72aa331fa5533c0e8a322e20c6444a6f57fc30bc73`
- The seven failures reproduce unchanged on the pre-repair candidate:
  `tests/test_d012.py::test_disposable_real_runtime_dry_run_and_process_audit`,
  `tests/test_d012_process_boundary.py::test_full_distinct_process_campaign`,
  `tests/test_d013ab_multineed_corridor.py::test_active_fatigue_recovery_uses_corridor_adjudication_once`,
  `tests/test_d013ab_multineed_corridor.py::test_integrity_and_stimulation_candidates_share_the_boundary`,
  `tests/test_d013ak_authority_reachability.py::test_default_13035_authority_retains_charge_without_changing_score`,
  `tests/test_d013h_v2_formal_readiness.py::test_real_perception_path_detects_material_resource_change`,
  `tests/test_d013y_integrated.py::test_cold_start_discovery_uses_physical_action_and_real_observation`.
- Candidate-only failures: `0`. The raw suite is not reported as wholly green;
  inherited failures remain visible and require their historical dispositions.

Collection and governance checks:

- `1394 tests collected`
- Authority 3.0: PASS
- Governance: PASS
- `git diff --check`: PASS
- Relevant changed Python modules: compile PASS

Literal AS-015 downstream preflight:

- `7/7 PASS`: lifecycle, boundedness, soak, and
  FULL/TERMINAL_READINESS_DISABLED/CONTINUATION_DISABLED/ROUTE_LEARNING_DISABLED/
  VIABILITY_KERNEL_DISABLED
- Every row had exit code `0`, final output and computed checkpoint present and
  equal, correct seed/directive binding, and no temporary publication files.
- Aggregate artifact:
  `AS017_LITERAL_DOWNSTREAM_PREFLIGHT_V1.json`
- Aggregate artifact SHA-256:
  `e0358db4996fc6a1f6a35ae4512ec7cc4e0db9c9d94bb72c921df34d1dfb00ad`
- The preflight CPJ result metadata records the successful invocation; its
  stdout SHA-256 is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Evidence scope and remaining gates

Transition conformance is covered by actual physiology/Governance semantics
and negative controls; it is not inferred from recovery linkage identifiers.
The 20 historical ORIENT heading values remain numerically unverified because
V5 did not retain pre-action orientation. Compound/recurring recovery and
observer neutrality remain scoped to their existing V5 evidence and are not
expanded by this packet. The seven inherited raw-suite failures are not
reclassified as candidate regressions, but their underlying current-capability
claims remain explicitly disclosed.

Formal lock, fresh population, lifecycle qualification, repeated-compaction
100k, real-time S3, causal ablation, essential-subsystem causal acceptance,
and believable-creature/CLOSE-03 acceptance remain NOT RUN or OPEN.
