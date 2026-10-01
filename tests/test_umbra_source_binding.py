from copy import deepcopy
import hashlib

import pytest

from tools.umbra_source_binding import capture_source_binding, validate_source_binding, verify_accepted_production


def test_current_source_and_loaded_dependency_closure_are_bound():
    binding = capture_source_binding()
    assert "umbra_core/recoverability/view.py" in binding["files"]
    assert "tools/as017_validate_linkage_v2.py" in binding["files"]
    assert binding["historical_execution_source_reconstructed"] is False
    assert validate_source_binding(binding, binding) == []
    # A new explicitly authorized semantic candidate must bind its own exact
    # committed production, not falsely advertise the predecessor's blobs.
    verify_accepted_production(binding["head"])


@pytest.mark.parametrize("mutation", ["changed_file", "missing_file", "extra_module", "runtime", "wrong_origin"])
def test_source_or_dependency_changes_fail_closed(mutation):
    expected = capture_source_binding()
    actual = deepcopy(expected)
    name = "umbra_core/recoverability/view.py"
    if mutation == "changed_file":
        actual["files"][name] = "0" * 64
    elif mutation == "missing_file":
        actual["files"].pop(name)
    elif mutation == "extra_module":
        actual["files"]["tools/unregistered.py"] = "a" * 64
    elif mutation == "wrong_origin":
        key = next(iter(actual["loaded_checkout_module_origins"]))
        current = actual["loaded_checkout_module_origins"][key]
        actual["loaded_checkout_module_origins"][key] = next(p for p in actual["files"] if p != current)
    else:
        actual["runtime"]["python"] = "different"
    assert validate_source_binding(expected, actual)


@pytest.mark.parametrize("mutation", ["changed_file", "extra_untracked_python"])
def test_actual_production_bytes_and_untracked_modules_cannot_evade_guard(tmp_path, monkeypatch, mutation):
    root = tmp_path
    folder = root / "umbra_core"
    folder.mkdir()
    path = folder / "example.py"
    content = b"accepted = True\n"
    path.write_bytes(content)
    digest = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    monkeypatch.setattr("tools.umbra_source_binding.subprocess.check_output",
                        lambda *a, **k: f"100644 blob {digest}\tumbra_core/example.py\0".encode())
    verify_accepted_production("synthetic", root)
    if mutation == "changed_file":
        path.write_bytes(b"accepted = False\n")
    else:
        (folder / "unregistered.py").write_bytes(b"unexpected = True\n")
    with pytest.raises(ValueError):
        verify_accepted_production("synthetic", root)
