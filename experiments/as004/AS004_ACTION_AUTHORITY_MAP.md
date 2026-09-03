# AS-004 ordinary authority map

The AS-004-enabled runtime uses one ordinary final-winner path:

`candidate generation → hard admissibility → common-root bounded continuation preservation → distributed evidence competition → candidate-local stochastic resolution → Governance → Embodiment → VerifiedOutcome`

The continuation bridge constructs its root before inspecting candidate-specific
metadata. It can remove a candidate only when a known continuation witness is
preserved by another candidate and destroyed by that candidate, with no
asymmetric `UNKNOWN`. It never creates or queues an action.

When `OrganismConfig.bounded_continuation_enabled` is false, historical runtime
behavior remains available for baseline comparison. When it is true, the
legacy ordinary `option.*` preservation channel and WorldModel planning/bias
proposal lane are bypassed so two preservation authorities cannot compete.

Critical recovery remains a separate hard authority and is not routed through
the ordinary continuation relation.
