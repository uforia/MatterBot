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


if __name__ == "__main__":
    unittest.main()
