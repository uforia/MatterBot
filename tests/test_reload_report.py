import matterbot


def test_format_reload_report_mixed():
    fn = matterbot.MattermostManager.format_reload_report
    mgr = object.__new__(matterbot.MattermostManager)
    msg = fn(mgr, {"added": ["a", "b"], "refreshed": ["c"],
                   "removed": ["d"], "failed": {"e": "SyntaxError(...)"}})
    assert "refreshed=1" in msg
    assert "added=2 (a, b)" in msg
    assert "removed=1 (d)" in msg
    assert "failed=1" in msg
    # failure detail rendered as a backtick-wrapped bullet line
    assert "- `e`: SyntaxError(...)" in msg


def test_format_reload_report_clean():
    fn = matterbot.MattermostManager.format_reload_report
    mgr = object.__new__(matterbot.MattermostManager)
    msg = fn(mgr, {"added": [], "refreshed": ["x", "y"],
                   "removed": [], "failed": {}})
    assert "refreshed=2" in msg and "failed=0" in msg
    assert "added=0" in msg and "removed=0" in msg
    # a clean run is a single line — no failure bullet section
    assert "\n" not in msg
