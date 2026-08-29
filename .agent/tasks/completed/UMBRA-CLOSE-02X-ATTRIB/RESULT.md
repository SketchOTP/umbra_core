# UMBRA-CLOSE-02X-ATTRIB result

Primary verdict: `CLOSE02XATTRIB_CROSS_DIMENSION_LIVENESS_REGRESSION`.

Secondary finding: `CLOSE02XATTRIB_FATIGUE_SUPPORT_UNAVAILABLE`.

The one authorized frozen-X diagnostic exactly reproduced R1/S16 seed `57531938`: `NO_SAFE_ACTION` tick 923 and critical fatigue tick 924. Fatigue entered preventive attention at tick 1 but never obtained `SUPPORTED_MARGIN_POSITIVE`; the first fully supported status at tick 124 was already `SUPPORTED_MARGIN_EXHAUSTED`.

The first energy constraint at tick 569 removed REST before per-candidate seeded stochastic scoring. U scored four candidates and X three. Although both selected the same APPROACH action at tick 569, candidate parameters diverged at tick 574, outcomes at 577, physiology at 578, and capability at 629. From ticks 569-924 X recorded 11 successful and 70 failed REST outcomes, versus U's 20 successful and 16 failed REST outcomes. This establishes a causal X-specific cross-dimension liveness regression, not a counterfactual rescue claim.

Recommendation: `REJECT_X_AS_FORWARD_PRODUCTION_CANDIDATE`. No automatic successor is authorized.
