import os
import sys
import time

import pytest

import command_loader

# CPython's .pyc cache keys on the source file's integer-second mtime.
# This test rewrites command.py twice within the same wall-clock second,
# so without forcing a strictly-newer mtime importlib.reload() would reuse
# stale bytecode. Real deployments `git pull` (mtime jumps forward well
# past a second), so this only models reality — it does not weaken any
# assertion.
_MTIME = [time.time() + 100000.0]


def _bump(*paths):
    _MTIME[0] += 10.0
    for p in paths:
        os.utime(p, (_MTIME[0], _MTIME[0]))

LOADER_BLOCK = '''
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(m):
    try:
        return import_module(f".{m}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(m)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
settings = SimpleNamespace(**{k: v for mod in (_defaults, _settings) if mod
                              for k, v in vars(mod).items()
                              if not k.startswith("__")})
'''


def _write(pkgdir, name, *, binds, chans=None, help_obj="__OMIT__",
           returns="v1", broken=False):
    moddir = pkgdir / name
    moddir.mkdir(parents=True, exist_ok=True)
    if broken:
        (moddir / "command.py").write_text("def process(  # syntax error\n")
        (moddir / "defaults.py").write_text("BINDS=%r\nCHANS=%r\n"
                                            % (binds, chans or ["debug"]))
        _bump(moddir / "command.py", moddir / "defaults.py")
        return
    d = "BINDS=%r\nCHANS=%r\n" % (binds, chans or ["debug"])
    if help_obj != "__OMIT__":
        d += "HELP=%r\n" % (help_obj,)
    (moddir / "defaults.py").write_text(d)
    (moddir / "command.py").write_text(
        LOADER_BLOCK
        + "\ndef process(command, channel, username, params, files, conn):\n"
        + "    return {'messages': [{'text': %r}]}\n" % returns)
    _bump(moddir / "defaults.py", moddir / "command.py")


@pytest.fixture
def tree(tmp_path):
    pkgdir = tmp_path / "cmds"
    pkgdir.mkdir()
    if str(tmp_path) not in sys.path:
        sys.path.insert(0, str(tmp_path))
    yield pkgdir
    for mod in [m for m in list(sys.modules) if m.split(".")[0] == "cmds"]:
        del sys.modules[mod]
    if str(tmp_path) in sys.path:
        sys.path.remove(str(tmp_path))


def test_first_load_builds_table(tree):
    _write(tree, "foo", binds=["foo"], help_obj={"DEFAULT": {"desc": "f"}})
    cmds, binds, report = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    assert set(cmds) == {"foo"}
    assert cmds["foo"]["binds"] == ["foo"]
    assert binds == ["foo"]
    assert cmds["foo"]["process"]("c", "ch", "u", [], [], None) == \
        {"messages": [{"text": "v1"}]}
    assert report["added"] == ["foo"]


def test_help_leak_is_fixed(tree):
    _write(tree, "foo", binds=["foo"], help_obj={"DEFAULT": {"desc": "f"}})
    _write(tree, "bar", binds=["bar"])  # help omitted
    cmds, _b, _r = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    assert cmds["foo"]["help"] == {"DEFAULT": {"desc": "f"}}
    assert cmds["bar"]["help"] is None


def test_reload_picks_up_changed_process(tree):
    _write(tree, "foo", binds=["foo"], returns="v1")
    cmds, _b, _r = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    _write(tree, "foo", binds=["foo"], returns="v2")
    cmds2, _b2, report = command_loader.load_command_table(
        str(tree), "cmds", existing=cmds, do_reload=True)
    assert cmds2["foo"]["process"]("c", "ch", "u", [], [], None) == \
        {"messages": [{"text": "v2"}]}
    assert report["refreshed"] == ["foo"]


def test_added_and_removed(tree):
    _write(tree, "foo", binds=["foo"])
    cmds, _b, _r = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    existing = {**cmds, "ghost": {"binds": ["ghost"], "chans": [],
                                  "process": (lambda *a: None), "help": None}}
    _write(tree, "baz", binds=["baz"])
    cmds2, binds2, report = command_loader.load_command_table(
        str(tree), "cmds", existing=existing, do_reload=True)
    assert "baz" in report["added"] and "ghost" in report["removed"]
    assert "ghost" not in cmds2
    assert "ghost" not in binds2 and "baz" in binds2


def test_broken_module_is_non_fatal_and_retains_previous(tree):
    _write(tree, "foo", binds=["foo"], returns="good")
    cmds, _b, _r = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    _write(tree, "good", binds=["good"])
    _write(tree, "foo", binds=["foo"], broken=True)
    cmds2, _b2, report = command_loader.load_command_table(
        str(tree), "cmds", existing=cmds, do_reload=True)
    assert "foo" in report["failed"]
    assert "good" in cmds2
    assert cmds2["foo"]["process"]("c", "ch", "u", [], [], None) == \
        {"messages": [{"text": "good"}]}


def test_chans_preserved_across_reload(tree):
    _write(tree, "foo", binds=["foo"])
    cmds, _b, _r = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    cmds["foo"]["chans"] = ["#operator-bound"]
    cmds2, _b2, _r2 = command_loader.load_command_table(
        str(tree), "cmds", existing=cmds, do_reload=True)
    assert cmds2["foo"]["chans"] == ["#operator-bound"]


def test_binds_preserved_across_reload(tree):
    # Symmetry with chans: a name already in `existing` with non-None binds
    # keeps those binds across reload (mirrors bindmap persistence), rather
    # than re-deriving them from the module's defaults.
    _write(tree, "foo", binds=["foo"])
    cmds, _b, _r = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    cmds["foo"]["binds"] = ["runtime-bound"]
    cmds2, binds2, _r2 = command_loader.load_command_table(
        str(tree), "cmds", existing=cmds, do_reload=True)
    assert cmds2["foo"]["binds"] == ["runtime-bound"]
    assert "runtime-bound" in binds2 and "foo" not in binds2


def test_case_insensitive_dir_collision_is_reported(tree, monkeypatch):
    # Two command dirs whose basenames collide after .lower() must surface
    # in report["failed"], not silently shadow each other. Simulate the walk
    # so the test is host-independent (macOS's FS is case-insensitive and
    # cannot hold both Foo/ and foo/).
    _write(tree, "foo", binds=["foo"], returns="v1")
    real_walk = os.walk

    def fake_walk(path):
        for root, dirs, files in real_walk(path):
            yield root, dirs, files
            if os.path.basename(root) == "foo":
                yield (os.path.join(os.path.dirname(root), "FOO"),
                       [], ["command.py"])

    monkeypatch.setattr(command_loader.os, "walk", fake_walk)
    _cmds, _b, report = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    assert "foo" in report["failed"]
    assert "collision" in report["failed"]["foo"].lower()


def test_returned_table_is_independent_of_existing(tree):
    _write(tree, "foo", binds=["foo"], returns="v1")
    cmds, _b, _r = command_loader.load_command_table(
        str(tree), "cmds", existing=None, do_reload=False)
    _write(tree, "foo", binds=["foo"], returns="v2")
    cmds2, _b2, _r2 = command_loader.load_command_table(
        str(tree), "cmds", existing=cmds, do_reload=True)
    # In-flight safety: the OLD table's process ref still runs the OLD code
    # after a reload, and the reload returns a NEW top-level dict (not the
    # same object mutated in place).
    assert cmds["foo"]["process"]("c", "ch", "u", [], [], None) == \
        {"messages": [{"text": "v1"}]}
    assert cmds2 is not cmds
