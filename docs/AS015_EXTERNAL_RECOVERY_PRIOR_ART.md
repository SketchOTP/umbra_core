# AS-015 external recovery prior-art disposition

## Scope

This is reference-only architecture review for AS-015. It does not import a
continuous controller, reward shaping, probability model, neural policy, or new
third-party dependency into UMBRA.

## Runtime shielding — reference

The review of shielding by Könighofer et al. notes that a shield is not
computable when no safe action exists, and that its guarantees are only as good
as its world model. This supports retaining UMBRA's conservative final
verified-outcome branch check rather than weakening it after a terminal state
has been reached. It does not authorize the project to adopt RL or a
probabilistic risk score.

Source: [Shields for Safe Reinforcement Learning](https://doi.org/10.1145/3715958).

## Controlled-invariant backup recovery — reference

Van Wijk et al. describe controlled-invariant sets and backup-control barrier
functions: safety depends on retaining a state from which an available backup
control can keep the system safe under the modeled uncertainty. This supports
the AS-015 architectural direction of blocking an ordinary action only when it
would eliminate the last source-backed robust recovery route. It does not make
historical UMBRA motion observations a physical guarantee.

Source: [Disturbance-Robust Backup Control Barrier Functions](https://doi.org/10.1109/LCSYS.2024.3514998).

## Runtime reachability to backup region — reference

Llanes, Abate, and Coogan describe runtime reachable-set checks against a known
backup-safe region. UMBRA will use the narrow categorical analogue: evaluate
authoritative effect branches plus unavoidable drift for policy-visible recovery
routes. No continuous reachable-set solver or geometric world-truth reader is
introduced.

Source: [Safety from in-the-loop reachability for cyber-physical systems](https://doi.org/10.1145/3457335.3461706).

## AS-015 disposition

The applicable transferable principle is preventive preservation of an existing
recoverable route, not a last-moment rescue. UMBRA's mechanism remains bounded,
categorical, source-backed, and subordinate to its existing verified-outcome
branch safety authority.
