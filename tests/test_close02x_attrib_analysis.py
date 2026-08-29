from experiments.close02x_attrib.analyze import first_difference


def test_first_difference_returns_tick_or_none():
    x = [{"tick": 1, "v": 1}, {"tick": 2, "v": 2}]
    u = [{"tick": 1, "v": 1}, {"tick": 2, "v": 3}]
    assert first_difference(x, u, lambda a, b: a["v"] != b["v"]) == 2
    assert first_difference(x, x, lambda a, b: a["v"] != b["v"]) is None
