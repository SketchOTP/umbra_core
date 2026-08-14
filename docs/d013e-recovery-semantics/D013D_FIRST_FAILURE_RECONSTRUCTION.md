# D-013D first-failure reconstruction

- Formal execution: `umbra-d013d-formal-e7d6d07-001`
- Tick: 138
- Energy before/after: `0.2495` / `0.2445`
- Energy floor crossed: no
- Perceived distance: `1.340481645595797`
- Confidence / uncertainty: `0.8974076415957972` / `0.10259235840420278`
- Authoritative distance: `1.5167094947389301`
- Resource radius: `1.2`; charge execution boundary: `1.5`
- Selected and executed capability: `CHARGE`
- Governance: admitted
- Embodiment: rejected, `not_at_resource`
- Verified outcome: success `false`, verified `true`
- Formal terminal reason: `charge_selected_but_not_executable`

The selection was based on an estimate inside the arbitration charge cutoff;
the denial was based on authoritative world state. The two values are
consistent with an uncertainty-preserving perception membrane and a
fail-closed embodiment boundary.
