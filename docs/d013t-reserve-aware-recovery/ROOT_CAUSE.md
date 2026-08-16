# Root cause

D-013S was caused by both:

1. Route-feasibility failure: the organism continued an energy-recovery route
   after the policy-visible remaining reserve was insufficient for the bounded
   route to an executable resource.
2. Same-variable safety exemption: the prospective critical-boundary check
   ignored the current focus, so the terminal APPROACH was allowed to move
   energy from 0.0525 to 0.0485.

The correction does not change the floor, action costs, charge benefit,
habitat, evaluator, contract, or schedule.
