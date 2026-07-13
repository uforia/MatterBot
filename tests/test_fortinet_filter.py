"""Regression tests for the fortinet feed's CVSS filter (issue #268).

When `settings.FILTER` is on, `query()` only builds `content` for an entry that
passes the CVSS threshold. An entry that does *not* pass used to fall straight
through to the description/append block, where `content` still held the
**previous** entry's title and link -- so the previous post was emitted a
second time with the new entry's description glued on, and on the very first
entry of a feed `content` was unbound entirely (NameError).

The module needs bs4/feedparser/requests, none of which are available to the
dependency-free `python -m unittest` CI runner, so they are stubbed here. The
stubs only need to satisfy the import and the two call sites the tests reach.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEED_PY = REPO_ROOT / "modules" / "fortinet" / "feed.py"


def _install_stub(name, **attrs):
    """Register a stand-in third-party module so feed.py can be imported."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _load_fortinet():
    _install_stub("bs4", BeautifulSoup=lambda *a, **kw: None)
    _install_stub("feedparser", parse=lambda *a, **kw: None)
    _install_stub(
        "requests",
        Session=lambda *a, **kw: None,
        exceptions=types.SimpleNamespace(RequestException=Exception),
    )
    spec = importlib.util.spec_from_file_location("fortinet_feed_under_test", FEED_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Entry:
    """Minimal stand-in for a feedparser entry."""

    def __init__(self, title, link):
        self.title = title
        self.link = link
        self.description = ""  # empty => the bs4 description branch is skipped


class _Feed:
    def __init__(self, entries):
        self.entries = entries


class _Score:
    """Stand-in for a bs4 element selected as a CVSS score cell."""

    def __init__(self, text):
        self.text = text


class FortinetFilterTests(unittest.TestCase):
    def setUp(self):
        self.fortinet = _load_fortinet()
        self.addCleanup(sys.modules.pop, "fortinet_feed_under_test", None)

        # Threshold is a constant for the run; stub it so the test needs no
        # opencve module on the path.
        self.fortinet.importScore = lambda: 7.0

        self.settings = {
            "NAME": "Fortinet",
            "URLS": ["https://example.invalid/feed"],
            "CHANNELS": ["news"],
            "ENTRIES": 3,
            "FILTER": True,
        }

    def _run(self, entries, scores):
        """Run query() over `entries`, with checkPage() returning scores[link]."""
        self.fortinet.feedparser.parse = lambda *a, **kw: _Feed(entries)
        self.fortinet.checkPage = lambda link: scores[link]
        return self.fortinet.query(dict(self.settings))

    def test_below_threshold_entry_is_not_posted(self):
        entries = [_Entry("Low severity", "https://example.invalid/low")]
        items = self._run(entries, {"https://example.invalid/low": ("cvss", "3.1")})
        self.assertEqual([], items)

    def test_below_threshold_entry_does_not_duplicate_the_previous_post(self):
        # The core of #268: a passing entry followed by a failing one must not
        # cause the passing entry to be posted twice.
        entries = [
            _Entry("Critical bug", "https://example.invalid/high"),
            _Entry("Cosmetic bug", "https://example.invalid/low"),
        ]
        items = self._run(
            entries,
            {
                "https://example.invalid/high": ("cvss", "9.8"),
                "https://example.invalid/low": ("cvss", "3.1"),
            },
        )
        self.assertEqual(1, len(items), f"expected only the high-CVSS entry, got {items}")
        channel, content = items[0]
        self.assertEqual("news", channel)
        self.assertIn("Critical bug", content)
        self.assertIn("9.8", content)
        self.assertNotIn("Cosmetic bug", content)

    def test_first_entry_below_threshold_does_not_raise(self):
        # Previously an unbound-local NameError, because `content` was never
        # assigned on the very first iteration.
        entries = [
            _Entry("Cosmetic bug", "https://example.invalid/low"),
            _Entry("Critical bug", "https://example.invalid/high"),
        ]
        items = self._run(
            entries,
            {
                "https://example.invalid/low": ("cvss", "3.1"),
                "https://example.invalid/high": ("cvss", "9.8"),
            },
        )
        self.assertEqual(1, len(items))
        self.assertIn("Critical bug", items[0][1])

    def test_above_threshold_entry_is_posted_with_its_score(self):
        entries = [_Entry("Critical bug", "https://example.invalid/high")]
        items = self._run(entries, {"https://example.invalid/high": ("cvss", "9.8")})
        self.assertEqual(1, len(items))
        self.assertIn("Fortinet: [Critical bug - CVSS: `9.8`]", items[0][1])
        self.assertIn("https://example.invalid/high", items[0][1])


class FortinetFilterPolarityTests(FortinetFilterTests):
    """Issue #269: FILTER used to *post* advisories whose severity was unknown."""

    def test_entry_with_no_cvss_on_the_page_is_not_posted(self):
        # checkPage() finds no score elements -> severity unknown -> must not post.
        entries = [_Entry("Unscored advisory", "https://example.invalid/none")]
        items = self._run(entries, {"https://example.invalid/none": []})
        self.assertEqual([], items)

    def test_entry_whose_page_failed_to_load_is_not_posted(self):
        # checkPage() returns False when the request raised -> severity unknown.
        entries = [_Entry("Unreachable advisory", "https://example.invalid/dead")]
        items = self._run(entries, {"https://example.invalid/dead": False})
        self.assertEqual([], items)

    def test_score_exactly_at_threshold_is_posted(self):
        entries = [_Entry("Borderline", "https://example.invalid/edge")]
        items = self._run(entries, {"https://example.invalid/edge": ("cvss", "7.0")})
        self.assertEqual(1, len(items))
        self.assertIn("CVSS: `7.0`", items[0][1])

    def test_zero_score_is_a_score_not_an_absent_one(self):
        # `if cvss:` used to treat a legitimate CVSS of 0.0 as "no score".
        self.fortinet.importScore = lambda: 0.0
        entries = [_Entry("Informational", "https://example.invalid/zero")]
        items = self._run(entries, {"https://example.invalid/zero": ("cvss", "0.0")})
        self.assertEqual(1, len(items))
        self.assertIn("CVSS: `0.0`", items[0][1])

    def test_highest_score_on_the_page_is_the_one_compared(self):
        # A page listing several CVEs must be judged on its most severe score.
        scores = [_Score("3.1"), _Score("9.1"), _Score("5.0")]
        entries = [_Entry("Multi-CVE advisory", "https://example.invalid/multi")]
        items = self._run(entries, {"https://example.invalid/multi": scores})
        self.assertEqual(1, len(items))
        self.assertIn("CVSS: `9.1`", items[0][1])

    def test_unparseable_score_cells_are_ignored(self):
        # Header/label cells swept up by the selector must not raise.
        scores = [_Score("CVSS Rating"), _Score("8.2")]
        entries = [_Entry("Advisory", "https://example.invalid/hdr")]
        items = self._run(entries, {"https://example.invalid/hdr": scores})
        self.assertEqual(1, len(items))
        self.assertIn("CVSS: `8.2`", items[0][1])


class FortinetThresholdHoistTests(FortinetFilterTests):
    """Issue #275: the threshold is a constant, but was re-read for every entry."""

    def test_threshold_is_read_once_per_run_not_once_per_entry(self):
        calls = []

        def counting_importScore():
            calls.append(1)
            return 7.0

        self.fortinet.importScore = counting_importScore
        self.settings["URLS"] = ["https://example.invalid/a", "https://example.invalid/b"]
        entries = [
            _Entry("One", "https://example.invalid/1"),
            _Entry("Two", "https://example.invalid/2"),
            _Entry("Three", "https://example.invalid/3"),
        ]
        scores = {e.link: ("cvss", "9.8") for e in entries}
        items = self._run(entries, scores)

        # 2 URLs x 3 entries = 6 posts, but importScore() re-runs a sys.path
        # insert and an import on every call, so it must run exactly once.
        self.assertEqual(6, len(items))
        self.assertEqual(1, len(calls), f"importScore() called {len(calls)}x, expected 1")

    def test_threshold_is_not_read_at_all_when_filtering_is_off(self):
        def exploding_importScore():
            raise AssertionError("importScore() must not run when FILTER is off")

        self.fortinet.importScore = exploding_importScore
        self.settings["FILTER"] = False
        entries = [_Entry("Anything", "https://example.invalid/x")]
        items = self._run(entries, {})
        self.assertEqual(1, len(items))
        self.assertIn("Fortinet: [Anything](https://example.invalid/x)", items[0][1])


if __name__ == "__main__":
    unittest.main()
