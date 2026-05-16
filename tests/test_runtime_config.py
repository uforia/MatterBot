import logging
import types
import runtime_config


def opts(matterbot=None, modules=None):
    return types.SimpleNamespace(Matterbot=matterbot or {}, Modules=modules or {})


def test_resolve_feedmap_prefers_matterbot_key():
    o = opts({"feedmap": "/var/lib/matterbot/feedmap.json"}, {"feedmap": "feedmap.json"})
    assert runtime_config.resolve_feedmap(o) == "/var/lib/matterbot/feedmap.json"


def test_resolve_feedmap_falls_back_to_modules_alias():
    assert runtime_config.resolve_feedmap(opts({}, {"feedmap": "legacy.json"})) == "legacy.json"


def test_resolve_feedmap_default_when_both_absent():
    assert runtime_config.resolve_feedmap(opts({}, {})) == "feedmap.json"


def test_configure_logging_stdout_on_dash(capsys):
    root = logging.getLogger()
    old = root.handlers[:]
    try:
        root.handlers = []
        runtime_config.configure_logging({"logfile": "-"}, debug=False)
        logging.getLogger("t").info("hello-stdout")
        assert "hello-stdout" in capsys.readouterr().out
    finally:
        root.handlers = old


def test_configure_logging_file_when_path_set(tmp_path):
    root = logging.getLogger()
    old = root.handlers[:]
    lf = tmp_path / "mb.log"
    try:
        root.handlers = []
        runtime_config.configure_logging({"logfile": str(lf)}, debug=False)
        logging.getLogger("t").info("hello-file")
        for h in root.handlers:
            h.flush()
        assert "hello-file" in lf.read_text()
    finally:
        root.handlers = old
