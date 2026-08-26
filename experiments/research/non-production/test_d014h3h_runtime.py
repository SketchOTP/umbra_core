import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from d014h3h_runtime import identity_selector_callback, run_one_tick, sentinel_selector_callback

def test_identity_hook_keeps_exact_action_path():
    ordinary = run_one_tick(None)
    hooked = run_one_tick(identity_selector_callback)
    assert ordinary["result"]["capability"] == hooked["result"]["capability"]
    assert ordinary["result"]["H"] == hooked["result"]["H"]
    assert ordinary["state"]["rng_state"] == hooked["state"]["rng_state"]
    assert ordinary["state"]["physiology"] == hooked["state"]["physiology"]
    assert hooked["trace"][0]["d014h3h_selector"]["post_selection_replacement_count"] == 0

def test_sentinel_is_constrained_to_captured_pool():
    result = run_one_tick(sentinel_selector_callback)
    selector_rows = [row for row in result["trace"] if "d014h3h_selector" in row]
    assert selector_rows
    row = selector_rows[0]
    selected = row["d014h3h_selector"]["selected_candidate"]
    pool = row["d014h3h_selector"]["candidate_pool"]
    assert any(
        selected["capability"] == candidate["capability"]
        and selected["params"] == candidate["params"]
        for candidate in pool
    )
    assert row["governance_proposal"]["capability"] == selected["capability"]
    assert row["governance_proposal"]["params"] == selected["params"]
    assert row["verified_outcome_linkage"]["capability"] == selected["capability"]
    assert row["d014h3h_selector"]["post_selection_replacement_count"] == 0
