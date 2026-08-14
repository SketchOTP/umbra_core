# Formal rule analysis

The D-012 P0 harness raises `charge_selected_but_not_executable` when the
selected candidate is `CHARGE` and body/habitat validation is not `ok` or the
verified outcome is unsuccessful. That rule is conservative, but it conflates
two states: an authority-preserving denial caused by uncertain perception and
an organism defect that cannot recover or respect authority.

D-013D demonstrates the former. The formal rule therefore produced a valid
formal failure under its frozen semantics, but the semantics are too strict to
classify this specific event as organism-level viability loss. D-013E does not
change that rule or any threshold.
