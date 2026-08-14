# V1 defect

The D-013D formal rule in `experiments/d012/organism_worker.py` raised
`charge_selected_but_not_executable` whenever CHARGE was selected and the
authoritative outcome was denied. The formal runner then emitted the V1
integrity failure immediately.

That conflated two states: the authority chain correctly rejected an
uncertain proposal, and the organism actually failed its recovery contract.
D-013E showed the first state and a bounded continuation with later approach
and successful charge outcomes. V2 separates them without changing the
organism or the historical verdict.
