"""Tests for feedhistory.PostHistory, the per-module "already posted" store.

matterfeed runs every feed module in a pebble worker with a hard timeout. On
timeout pebble terminates the worker outright, so nothing after the kill runs.
The original implementation kept the history as one pickled list in a
`shelve` opened with writeback=True and persisted it only in `finally` -- after
every post of the run had already been sent to Mattermost. A worker killed
between its first post and that final sync therefore re-sent the same items on
the next cycle, and the next, forever: the "looping newsfeed". Because the list
was never pruned, that final sync also grew without bound, so the kill became
more likely the longer the bot had been running.

The contract tested here is the fix: a post is durable the moment it is
recorded, independent of close(), and recording cost does not grow with the
size of the history.

feedhistory is kept stdlib-only so it runs under the dependency-free
`python -m unittest` CI runner, like feedutils.
"""

import ast
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import feedhistory


POST_A = ["news", "Vendor: [Title](https://example.com/a)", []]
POST_B = ["news", "Vendor: [Title](https://example.com/b)", []]
POST_WITH_UPLOAD = ["news", "Vendor: [Img](https://example.com/c)",
                    {"uploads": [{"filename": "c.png", "bytes": b"\x89PNG\x00\x01"}]}]


class PostHistoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "vendor.cache")

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_open_is_first_run(self):
        with feedhistory.PostHistory(self.path, "vendor") as history:
            self.assertTrue(history.first_run)

    def test_second_open_is_not_first_run_even_if_nothing_was_recorded(self):
        # The first cycle only seeds the history, it posts nothing. The marker
        # that says "this module has been seen before" must survive on its own.
        feedhistory.PostHistory(self.path, "vendor").close()
        with feedhistory.PostHistory(self.path, "vendor") as history:
            self.assertFalse(history.first_run)

    def test_record_is_durable_when_the_recording_process_is_killed(self):
        # The worker can be killed at any moment after a post went out. A post
        # that was recorded must be visible to the next run even though the
        # recording process never reached close(). os._exit() skips every
        # finally/atexit/destructor, which is what a pebble timeout kill does.
        worker = textwrap.dedent(f"""
            import os, sys
            sys.path.insert(0, {str(ROOT)!r})
            import feedhistory
            history = feedhistory.PostHistory({self.path!r}, "vendor")
            history.record({POST_A!r})
            os._exit(0)
        """)
        subprocess.run([sys.executable, "-c", worker], check=True, timeout=30)
        with feedhistory.PostHistory(self.path, "vendor") as history:
            self.assertTrue(history.seen(POST_A))
            self.assertFalse(history.seen(POST_B))

    def test_seen_matches_the_whole_post(self):
        with feedhistory.PostHistory(self.path, "vendor") as history:
            history.record(POST_A)
            self.assertTrue(history.seen(POST_A))
            self.assertTrue(history.seen(list(POST_A)))
            self.assertFalse(history.seen(["other-channel", POST_A[1], POST_A[2]]))
            self.assertFalse(history.seen([POST_A[0], POST_A[1] + "!", POST_A[2]]))

    def test_uploads_with_bytes_are_hashable_and_not_stored(self):
        with feedhistory.PostHistory(self.path, "vendor") as history:
            history.record(POST_WITH_UPLOAD)
            self.assertTrue(history.seen(POST_WITH_UPLOAD))
            different_bytes = ["news", POST_WITH_UPLOAD[1],
                               {"uploads": [{"filename": "c.png", "bytes": b"\x89PNG\x00\x02"}]}]
            self.assertFalse(history.seen(different_bytes))
        # The store holds a digest, never the attachment itself: history size
        # must not scale with media size (that growth is what pushed the final
        # sync past the worker timeout in the first place).
        size = sum(p.stat().st_size for p in Path(self._tmp.name).iterdir())
        self.assertLess(size, 64 * 1024)

    def test_legacy_list_history_is_migrated(self):
        # Pre-fix caches hold one pickled list of posts under the module name.
        # Those posts must count as seen (no re-posting the whole backlog on
        # upgrade), and the list itself must no longer be the thing that grows.
        import shelve
        with shelve.open(self.path, writeback=True) as legacy:
            legacy["vendor"] = [POST_A, POST_WITH_UPLOAD]
        with feedhistory.PostHistory(self.path, "vendor") as history:
            self.assertFalse(history.first_run)
            self.assertTrue(history.seen(POST_A))
            self.assertTrue(history.seen(POST_WITH_UPLOAD))
            self.assertFalse(history.seen(POST_B))
        with shelve.open(self.path) as migrated:
            self.assertNotIsInstance(migrated.get("vendor"), list,
                                     "legacy list must be replaced after migration")

    def test_posts_older_than_retention_are_forgotten_on_open(self):
        # The store must be bounded by the feeds' rate, not the bot's uptime:
        # a key older than the retention window is dropped the next time the
        # history is opened, and a younger one is kept.
        import shelve
        with feedhistory.PostHistory(self.path, "vendor", retention_days=90) as history:
            history.record(POST_A)
            history.record(POST_B)
        with shelve.open(self.path) as db:
            db[feedhistory.post_key(POST_A)] = time.time() - 91 * 86400
            db[feedhistory.post_key(POST_B)] = time.time() - 89 * 86400
        with feedhistory.PostHistory(self.path, "vendor", retention_days=90) as history:
            self.assertFalse(history.first_run)
            self.assertFalse(history.seen(POST_A))
            self.assertTrue(history.seen(POST_B))

    def test_key_is_stable_across_processes(self):
        # Keys are derived, not id()-based or hash()-randomised: the same post
        # must map to the same key in a fresh interpreter (PYTHONHASHSEED varies).
        self.assertEqual(feedhistory.post_key(POST_A), feedhistory.post_key(list(POST_A)))
        self.assertNotEqual(feedhistory.post_key(POST_A), feedhistory.post_key(POST_B))
        self.assertIsInstance(feedhistory.post_key(POST_WITH_UPLOAD), str)


class MatterfeedWiringTests(unittest.TestCase):
    """matterfeed.py cannot be imported under the stdlib runner (pebble,
    configargparse, mattermostdriver), so the wiring is asserted on its AST."""

    SOURCE = (ROOT / "matterfeed.py").read_text()

    def _run_module(self):
        for node in ast.walk(ast.parse(self.SOURCE)):
            if isinstance(node, ast.FunctionDef) and node.name == "runModule":
                return node
        self.fail("runModule not found in matterfeed.py")

    def test_run_module_uses_post_history_not_a_writeback_shelve(self):
        src = ast.get_source_segment(self.SOURCE, self._run_module())
        self.assertNotIn("shelve.open", src,
                         "runModule must go through feedhistory.PostHistory")
        self.assertNotIn("writeback", src)
        self.assertIn("PostHistory", src)

    def test_run_module_records_each_post_as_it_is_sent(self):
        # The record must happen inside the per-post loop, not deferred to a
        # single sync after all posts went out.
        src = ast.get_source_segment(self.SOURCE, self._run_module())
        self.assertIn(".record(", src)
        self.assertNotIn(".sync()", src)


if __name__ == "__main__":
    unittest.main()
