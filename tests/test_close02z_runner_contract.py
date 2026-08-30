import ast
from pathlib import Path

from experiments.close02z.compatibility import DIRECTIVE, STAGES


def test_runner_contains_only_two_authorized_diagnostics_in_order():
    assert DIRECTIVE == "UMBRA-CLOSE-02Z"
    assert [stage["stage"] for stage in STAGES] == ["DIAGNOSTIC_A", "DIAGNOSTIC_B"]
    assert [(stage["regime"], stage["seed"], stage["horizon"]) for stage in STAGES] == [
        ("R0", 45878900, 500),
        ("R0", 22023239, 3500),
    ]


def test_runner_cannot_open_known_r1_or_population_stages():
    source = Path("experiments/close02z/compatibility.py").read_text()
    tree = ast.parse(source)
    constants = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)}
    assert 57531938 not in constants
    assert not any(
        isinstance(value, str) and ("FORMAL" in value or "DEVELOPMENT" in value)
        for value in constants
    )


def test_runner_has_no_retry_or_reseed_loop():
    tree = ast.parse(Path("experiments/close02z/compatibility.py").read_text())
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "retry" not in names
    assert "reseed" not in names
