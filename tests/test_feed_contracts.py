"""Smoke test for the feed-module load contract.

`matterfeed.callModule` loads each `modules/<name>/feed.py` and calls its
top-level `query` function (settings come from `defaults.py`/`settings.py`).
A module that is missing that entry point, has a syntax error, or lacks
`defaults.py` fails silently at runtime — the feed just goes quiet.

These tests (a) unit-test the static contract checker against synthetic
fixtures, and (b) assert every real feed module in `modules/` satisfies the
contract, so a malformed new feed is caught before it ships. The check is
static (AST-only), so it needs none of the feeds' third-party dependencies.
"""

import os
import tempfile
import unittest
from pathlib import Path

from feed_audit import audit_feed_modules, check_feed_module

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_module(root, name, feed_src=None, defaults_src="NAME = 'x'\n"):
    moddir = os.path.join(root, name)
    os.makedirs(moddir)
    if feed_src is not None:
        with open(os.path.join(moddir, "feed.py"), "w", encoding="utf-8") as fh:
            fh.write(feed_src)
    if defaults_src is not None:
        with open(os.path.join(moddir, "defaults.py"), "w", encoding="utf-8") as fh:
            fh.write(defaults_src)
    return moddir


class CheckFeedModuleTests(unittest.TestCase):
    def test_valid_module_has_no_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_module(tmp, "good", "def query(settings):\n    return []\n")
            self.assertEqual([], check_feed_module(d))

    def test_missing_query_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_module(tmp, "noentry", "def other():\n    pass\n")
            violations = check_feed_module(d)
            self.assertEqual(1, len(violations))
            self.assertIn("query", violations[0])

    def test_async_query_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_module(tmp, "asyncmod", "async def query(settings):\n    return []\n")
            self.assertEqual([], check_feed_module(d))

    def test_syntax_error_in_feed_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_module(tmp, "broken", "def query(:\n    pass\n")
            violations = check_feed_module(d)
            self.assertTrue(any("syntax" in v for v in violations))

    def test_missing_feed_py_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_module(tmp, "nofeed", feed_src=None)
            self.assertTrue(any("feed.py" in v for v in check_feed_module(d)))

    def test_missing_defaults_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_module(tmp, "nodefaults", "def query(settings):\n    return []\n", defaults_src=None)
            self.assertTrue(any("defaults.py" in v for v in check_feed_module(d)))


class RealFeedTreeSmokeTest(unittest.TestCase):
    def test_every_feed_module_satisfies_the_load_contract(self):
        violations = audit_feed_modules(REPO_ROOT / "modules")
        self.assertEqual(
            {},
            violations,
            msg="feed modules violating the load contract: "
            + "; ".join(f"{m}: {vs}" for m, vs in violations.items()),
        )


if __name__ == "__main__":
    unittest.main()
