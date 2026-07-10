"""Tests for the feed-module return contract (feedutils.FeedResult).

A `query()` may return either the legacy plain list of posts, or a
`feedutils.FeedResult(items, errors)` that also carries the per-source errors
the module hit. `matterfeed.callModule` funnels both through
`feedutils.split_result`, logs any errors centrally, and hands the posts back
unchanged -- so a module can report a partial failure (one feed of several
returned a 403) without either swallowing it silently or raising and throwing
away the posts it already collected.

These tests cover that normalisation logic. They import only `feedutils`,
which is kept stdlib-only (bs4 is imported lazily) so it runs under the
dependency-free `python -m unittest` CI runner.
"""

import sys
import unittest
from pathlib import Path

# feedutils lives in modules/, which is not on the path under the test runner.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "modules"))

import feedutils


class SplitResultTests(unittest.TestCase):
    def test_plain_list_return_has_no_errors(self):
        items, errors = feedutils.split_result([["news", "a"], ["news", "b"]])
        self.assertEqual([["news", "a"], ["news", "b"]], items)
        self.assertEqual([], errors)

    def test_none_return_is_empty(self):
        self.assertEqual(([], []), feedutils.split_result(None))

    def test_feedresult_exposes_items_and_errors(self):
        r = feedutils.result(items=[["news", "a"]], errors=[("http://x/feed", "403 blocked")])
        items, errors = feedutils.split_result(r)
        self.assertEqual([["news", "a"]], items)
        self.assertEqual([("http://x/feed", "403 blocked")], errors)

    def test_partial_result_keeps_items_alongside_errors(self):
        # The entire point of the contract: report a failed source AND still
        # return everything that was collected.
        r = feedutils.result(items=[["news", "kept"]], errors=[("feed-2", "timeout")])
        items, errors = feedutils.split_result(r)
        self.assertEqual([["news", "kept"]], items)
        self.assertEqual(1, len(errors))

    def test_split_result_of_plain_list_returns_a_copy(self):
        # callModule/runModule mutate the returned list; that must not mutate
        # the caller's input.
        src = [["news", "a"]]
        items, _ = feedutils.split_result(src)
        items.append(["news", "b"])
        self.assertEqual([["news", "a"]], src)


class ResultFactoryTests(unittest.TestCase):
    def test_empty_result_is_two_empty_lists(self):
        r = feedutils.result()
        self.assertEqual([], r.items)
        self.assertEqual([], r.errors)
        self.assertEqual(([], []), feedutils.split_result(r))

    def test_result_copies_its_inputs(self):
        # A module often passes its own working list; result() must not alias
        # it, or later mutation would corrupt the returned FeedResult.
        src_items = [["news", "a"]]
        src_errors = [("feed", "err")]
        r = feedutils.result(items=src_items, errors=src_errors)
        src_items.append(["news", "b"])
        src_errors.append(("feed2", "err2"))
        self.assertEqual([["news", "a"]], r.items)
        self.assertEqual([("feed", "err")], r.errors)

    def test_is_a_named_2_tuple(self):
        r = feedutils.result(items=[1], errors=[2])
        self.assertEqual((([1]), ([2])), (r.items, r.errors))
        # namedtuple: unpackable and indexable, so existing list-style handling
        # of a FeedResult (were one passed straight through) still degrades
        # predictably rather than raising oddly.
        items, errors = r
        self.assertEqual([1], items)
        self.assertEqual([2], errors)


if __name__ == "__main__":
    unittest.main()
