from experiments.close02x_attrib.diagnostic import _stable_summary


def test_stable_summary_excludes_only_elapsed_time():
    row = {"ticks": 16, "actions": {"REST": 2}, "elapsed_seconds": 1.25}
    assert _stable_summary(row) == {"ticks": 16, "actions": {"REST": 2}}
