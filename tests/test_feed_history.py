"""Tests for feedhistory.PostHistory, the per-module "already posted" store.

The feed worker runs under a pebble timeout that kills it outright, so a post
must be durable the moment it is recorded, not at close(); a first run must
only count once the whole seed completed; and the store must stay bounded by
the feeds' rate, not the bot's uptime. feedhistory.py's docstring has the
incident behind each of these.

feedhistory is stdlib-only so this runs under the dependency-free CI runner.
"""

import ast
import os
import shelve
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import feedhistory  # noqa: E402


POST_A = ["news", "Vendor: [Title](https://example.com/a)", []]
POST_B = ["news", "Vendor: [Title](https://example.com/b)", []]
POST_WITH_UPLOAD = ["news", "Vendor: [Img](https://example.com/c)",
                    {"uploads": [{"filename": "c.png", "bytes": b"\x89PNG\x00\x01"}]}]
DAY = 86400


class PostHistoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "vendor.cache")

    def tearDown(self):
        self._tmp.cleanup()

    def open(self, **kwargs):
        return feedhistory.PostHistory(self.path, "vendor", **kwargs)

    def cache_files(self):
        return sorted(p.name for p in Path(self._tmp.name).iterdir())

    def cache_size(self):
        return sum(p.stat().st_size for p in Path(self._tmp.name).iterdir())

    # -- first run -------------------------------------------------------------

    def test_first_open_is_first_run(self):
        with self.open() as history:
            self.assertTrue(history.first_run)

    def test_first_run_persists_only_when_completed(self):
        # The seed can be killed halfway. Until complete_first_run() ran, the
        # next open must still be a first run, or the unseeded remainder is
        # posted as a flood of "new" items.
        with self.open() as history:
            history.record(POST_A)
        with self.open() as history:
            self.assertTrue(history.first_run)
            self.assertTrue(history.seen(POST_A), "partial seed is kept, not redone")
            history.complete_first_run()
        with self.open() as history:
            self.assertFalse(history.first_run)

    def test_completed_first_run_with_nothing_recorded_still_counts(self):
        with self.open() as history:
            history.complete_first_run()
        with self.open() as history:
            self.assertFalse(history.first_run)

    # -- durability ------------------------------------------------------------

    def test_record_is_durable_when_the_recording_process_is_killed(self):
        # os._exit() skips every finally/atexit/destructor, which is what a
        # pebble timeout kill does to the worker.
        worker = textwrap.dedent(f"""
            import os, sys
            sys.path.insert(0, {str(ROOT)!r})
            import feedhistory
            history = feedhistory.PostHistory({self.path!r}, "vendor")
            history.record({POST_A!r})
            os._exit(0)
        """)
        subprocess.run([sys.executable, "-c", worker], check=True, timeout=30)
        with self.open() as history:
            self.assertTrue(history.seen(POST_A))
            self.assertFalse(history.seen(POST_B))

    # -- identity --------------------------------------------------------------

    def test_seen_matches_the_whole_post(self):
        with self.open() as history:
            history.record(POST_A)
            self.assertTrue(history.seen(POST_A))
            self.assertTrue(history.seen(list(POST_A)))
            self.assertFalse(history.seen(["other-channel", POST_A[1], POST_A[2]]))
            self.assertFalse(history.seen([POST_A[0], POST_A[1] + "!", POST_A[2]]))

    def test_uploads_with_bytes_are_hashable_and_not_stored(self):
        with self.open() as history:
            history.record(POST_WITH_UPLOAD)
            self.assertTrue(history.seen(POST_WITH_UPLOAD))
            different_bytes = ["news", POST_WITH_UPLOAD[1],
                               {"uploads": [{"filename": "c.png", "bytes": b"\x89PNG\x00\x02"}]}]
            self.assertFalse(history.seen(different_bytes))
        # A digest, never the attachment: size must not scale with media.
        self.assertLess(self.cache_size(), 64 * 1024)

    def test_key_is_total_over_feed_text(self):
        # Feed JSON can carry a lone surrogate (server-side truncated emoji).
        # The key must still be derivable, or that one item aborts the run.
        lone_surrogate = ["news", "Vendor: broken \ud83d emoji", []]
        with self.open() as history:
            history.record(lone_surrogate)
            self.assertTrue(history.seen(lone_surrogate))

    def test_unidentifiable_post_raises_bad_post_not_store_error(self):
        # A module bug (a datetime inside the post) must be distinguishable
        # from a store failure, so the caller can skip that one post instead
        # of stopping the run.
        import datetime
        bad = ["news", "Vendor: x", {"uploads": [], "fetched": datetime.datetime(2026, 1, 1)}]
        with self.open() as history:
            with self.assertRaises(feedhistory.BadPost):
                history.seen(bad)
            with self.assertRaises(feedhistory.BadPost):
                history.record(bad)
            history.record(POST_A)  # the store is still usable afterwards
            self.assertTrue(history.seen(POST_A))

    def test_seen_without_refresh_does_not_write(self):
        with self.open() as history:
            history.record(POST_A)
            history.complete_first_run()
        old = time.time() - 30 * DAY
        with shelve.open(self.path) as db:
            db[feedhistory.post_key(POST_A)] = old
        with self.open() as history:
            self.assertTrue(history.seen(POST_A, refresh=False))
        with shelve.open(self.path) as db:
            self.assertEqual(old, db[feedhistory.post_key(POST_A)])

    def test_key_does_not_depend_on_interpreter_hash_seed(self):
        worker = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})
            import feedhistory
            print(feedhistory.post_key({POST_WITH_UPLOAD!r}))
        """)
        keys = set()
        for seed in ("1", "2"):
            out = subprocess.run([sys.executable, "-c", worker], check=True, timeout=30,
                                 capture_output=True, text=True,
                                 env={**os.environ, "PYTHONHASHSEED": seed})
            keys.add(out.stdout.strip())
        self.assertEqual(1, len(keys))
        self.assertEqual(keys.pop(), feedhistory.post_key(POST_WITH_UPLOAD))

    # -- retention -------------------------------------------------------------

    def test_posts_not_seen_for_retention_are_forgotten(self):
        with self.open(retention_days=90) as history:
            history.record(POST_A)
            history.record(POST_B)
            history.complete_first_run()
        with shelve.open(self.path) as db:
            db[feedhistory.post_key(POST_A)] = time.time() - 91 * DAY
            db[feedhistory.post_key(POST_B)] = time.time() - 89 * DAY
        with self.open(retention_days=90) as history:
            self.assertEqual(1, history.pruned)
            self.assertFalse(history.seen(POST_A))
            self.assertTrue(history.seen(POST_B))

    def test_a_post_still_served_by_its_feed_stays_seen(self):
        # Retention counts from the last time the item was seen, not the first
        # time it was posted: a feed that serves the same item for a year
        # (wiki pages, category listings) must not re-announce it every 90 days.
        with self.open(retention_days=90) as history:
            history.record(POST_A)
            history.complete_first_run()
        with shelve.open(self.path) as db:
            db[feedhistory.post_key(POST_A)] = time.time() - 80 * DAY
        with self.open(retention_days=90) as history:
            self.assertTrue(history.seen(POST_A))      # refreshes the timestamp
        with shelve.open(self.path) as db:
            db[feedhistory._PRUNED_AT] = 0             # force a sweep next open
        with self.open(retention_days=90) as history:
            self.assertEqual(0, history.pruned)
            self.assertTrue(history.seen(POST_A))

    def test_prune_runs_at_most_once_a_day(self):
        with self.open() as history:
            history.record(POST_A)
            history.complete_first_run()
        with shelve.open(self.path) as db:
            db[feedhistory.post_key(POST_A)] = time.time() - 365 * DAY
            db[feedhistory._PRUNED_AT] = time.time() - 3600
        with self.open() as history:
            self.assertEqual(0, history.pruned, "swept an hour ago: skip the scan")
            self.assertTrue(history.seen(POST_A))

    # -- upgrade and recovery --------------------------------------------------

    def test_legacy_list_cache_is_discarded_and_module_reseeds(self):
        # The old format: one pickled list of full posts (attachment bytes
        # included) under the module name. It is never unpickled -- the file
        # is recreated -- and the module runs a first run, which records the
        # current feed and posts nothing, so the upgrade re-posts nothing.
        big = ["news", "Vendor: [Img](https://example.com/big)",
               {"uploads": [{"filename": "big.png", "bytes": b"\x00" * 200_000}]}]
        with shelve.open(self.path, writeback=True) as legacy:
            legacy["vendor"] = [POST_A, big]
        before = self.cache_size()
        self.assertGreater(before, 200_000)
        with self.open() as history:
            self.assertTrue(history.legacy_discarded)
            self.assertTrue(history.first_run)
            self.assertFalse(history.seen(POST_A))
            history.record(POST_A)
            history.complete_first_run()
        self.assertLess(self.cache_size(), 64 * 1024, "file was recreated, not just a key deleted")
        with self.open() as history:
            self.assertFalse(history.first_run)
            self.assertFalse(history.legacy_discarded)
            self.assertTrue(history.seen(POST_A))

    def test_empty_legacy_list_is_also_discarded(self):
        with shelve.open(self.path, writeback=True) as legacy:
            legacy["vendor"] = []
        with self.open() as history:
            self.assertTrue(history.legacy_discarded)
            self.assertTrue(history.first_run)

    def test_unreadable_store_is_moved_aside_and_reseeded(self):
        # A kill mid-write can leave a gdbm/ndbm file unreadable. Failing on
        # every cycle until an operator deletes the file by hand is the manual
        # fix this module exists to retire.
        with open(self.path, "wb") as f:
            f.write(b"not a database" * 100)
        with self.open() as history:
            self.assertIsNotNone(history.recovered_from)
            self.assertTrue(history.first_run)
            history.complete_first_run()
        names = self.cache_files()
        self.assertTrue(any(".unreadable-" in n for n in names), names)
        with self.open() as history:
            self.assertFalse(history.first_run)
            self.assertIsNone(history.recovered_from)

    @unittest.skipIf(os.geteuid() == 0, "root ignores file modes")
    def test_permission_error_is_not_treated_as_corruption(self):
        # dbm.error includes OSError. A healthy history that is merely
        # unreadable right now (permissions, lock, full disk) must propagate,
        # not be moved aside and replaced by an empty store.
        with self.open() as history:
            history.record(POST_A)
            history.complete_first_run()
        files = self.cache_files()
        for name in files:
            os.chmod(Path(self._tmp.name) / name, 0)
        try:
            with self.assertRaises(OSError):
                self.open()
        finally:
            for name in files:
                os.chmod(Path(self._tmp.name) / name, 0o600)
        self.assertEqual(files, self.cache_files(), "nothing moved aside")
        with self.open() as history:
            self.assertFalse(history.first_run)
            self.assertTrue(history.seen(POST_A))


class MatterfeedWiringTests(unittest.TestCase):
    """matterfeed.py cannot be imported under the stdlib runner (pebble,
    configargparse, mattermostdriver), so the wiring is asserted on its AST."""

    @classmethod
    def setUpClass(cls):
        tree = ast.parse((ROOT / "matterfeed.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "runModule":
                cls.run_module = node
                return
        raise AssertionError("runModule not found in matterfeed.py")

    def _calls(self):
        for node in ast.walk(self.run_module):
            if isinstance(node, ast.Call):
                yield node

    @staticmethod
    def _dotted(func):
        if isinstance(func, ast.Attribute):
            return MatterfeedWiringTests._dotted(func.value) + "." + func.attr
        if isinstance(func, ast.Name):
            return func.id
        return ""

    def test_run_module_uses_post_history_not_a_writeback_shelve(self):
        names = [self._dotted(c.func) for c in self._calls()]
        self.assertNotIn("shelve.open", names)
        self.assertIn("feedhistory.PostHistory", names)
        for call in self._calls():
            self.assertFalse(any(k.arg == "writeback" for k in call.keywords))

    def test_run_module_records_inside_the_per_post_loop_and_never_syncs(self):
        names = [self._dotted(c.func) for c in self._calls()]
        self.assertNotIn("history.sync", names)
        in_loop = [self._dotted(c.func)
                   for loop in ast.walk(self.run_module) if isinstance(loop, ast.For)
                   for c in ast.walk(loop) if isinstance(c, ast.Call)]
        self.assertIn("history.record", in_loop)

    def test_run_module_completes_first_run_only_when_the_feed_returned_items(self):
        # callModule folds a failed fetch into an empty list (feedparser never
        # raises), so the gate must be on `items` being non-empty, not on it
        # being non-None: a feed that is down during its first run must not be
        # marked seeded-empty and then posted whole as "new" when it is back.
        for node in ast.walk(self.run_module):
            if isinstance(node, ast.If):
                calls = {self._dotted(c.func) for c in ast.walk(node) if isinstance(c, ast.Call)}
                if "history.complete_first_run" in calls:
                    test = ast.dump(node.test)
                    self.assertIn("Name(id='items'", test)
                    self.assertNotIn("Constant(value=None)", test,
                                     "gate on truthiness of items, not `is not None`")
                    return
        self.fail("no `if` guards complete_first_run")

    def test_run_module_completes_first_run_outside_the_loop(self):
        in_loop = {self._dotted(c.func)
                   for loop in ast.walk(self.run_module) if isinstance(loop, ast.For)
                   for c in ast.walk(loop) if isinstance(c, ast.Call)}
        names = [self._dotted(c.func) for c in self._calls()]
        self.assertIn("history.complete_first_run", names)
        self.assertNotIn("history.complete_first_run", in_loop)


if __name__ == "__main__":
    unittest.main()
