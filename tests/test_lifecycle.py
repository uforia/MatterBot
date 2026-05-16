import types
import lifecycle


def opts(mb):
    return types.SimpleNamespace(Matterbot=mb, Modules={}, debug=False)


def test_detect_explicit_none():
    assert lifecycle.detect_service_manager(opts({"service_manager": "none"}),
                                            env={"INVOCATION_ID": "x"}) == "none"


def test_detect_systemd_via_env():
    assert lifecycle.detect_service_manager(opts({"service_manager": "systemd"}),
                                            env={"INVOCATION_ID": "abc"}) == "systemd"


def test_detect_configured_systemd_but_not_under_it():
    assert lifecycle.detect_service_manager(opts({"service_manager": "systemd"}),
                                            env={}) == "none"

def test_state_dir_is_bindmap_parent(tmp_path):
    o = opts({"bindmap": str(tmp_path / "sub" / "bindmap.json")})
    assert lifecycle.state_dir(o) == (tmp_path / "sub")


def test_restart_marker_roundtrip(tmp_path):
    o = opts({"bindmap": str(tmp_path / "bindmap.json")})
    assert lifecycle.read_restart_marker(o) is None
    lifecycle.write_restart_marker(o, "C1", "R1")
    m = lifecycle.read_restart_marker(o)
    assert m["channel_id"] == "C1" and m["root_id"] == "R1"
    lifecycle.clear_restart_marker(o)
    assert lifecycle.read_restart_marker(o) is None


def test_self_reexec_calls_execv(monkeypatch):
    seen = {}
    monkeypatch.setattr(lifecycle.os, "execv",
                        lambda p, a: seen.update(p=p, a=a))
    lifecycle.self_reexec()
    assert seen["p"] == lifecycle.sys.executable
    assert seen["a"][0] == lifecycle.sys.executable
