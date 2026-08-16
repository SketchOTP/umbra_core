# Reconstructed pre-failure recovery window

The complete D-013S traces remain authoritative and unchanged.

## Recovery onset

- Energy first fell below viable_low=0.30 after tick 119, at 0.2995.
- Energy was the active recovery focus at tick 120.
- The first recovery opportunity was already executable in the initial
  recovery episode; the later formal trajectory contained multiple successful
  charge episodes before the terminal route.

## Terminal route window

The final 20-30 relevant ticks were inspected. The decisive observable window
is ticks 409-414:

| tick | energy before | estimated distance | authoritative distance | action | energy effect | safe reserve | bounded route cost |
|---:|---:|---:|---:|---|---:|---:|---:|
| 409 | 0.0725 | 9.3039 | 9.3899 | APPROACH | -0.004 | 0.0225 | 0.034 |
| 410 | 0.0685 | 8.4147 | 8.4067 | APPROACH | -0.004 | 0.0185 | 0.028 |
| 411 | 0.0645 | 7.4873 | 7.4376 | APPROACH | -0.004 | 0.0145 | 0.022 |
| 412 | 0.0605 | 6.3783 | 6.4396 | APPROACH | -0.004 | 0.0105 | 0.022 |
| 413 | 0.0565 | 5.2445 | 5.4592 | APPROACH | -0.004 | 0.0065 | 0.016 |
| 414 | 0.0525 | 5.0120 | 4.4675 | APPROACH | -0.004 | 0.0025 | 0.016 |

The route cost uses policy-visible estimated distance, the existing 1.5 charge
selection boundary, 1.5 recovery approach step, the known -0.004 APPROACH
effect, and one -0.002 autonomous drift interval between later actions.

The route first became observably infeasible at tick 409. The resource
distance decreased, but the remaining reserve could not safely fund the
bounded number of approaches required to reach an executable charge.

Classification: BOTH. The route-feasibility failure began earlier, and the
same-variable focus exemption allowed the terminal APPROACH to cross the
critical floor.
