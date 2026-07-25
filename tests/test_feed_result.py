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


class MalformedErrorTests(unittest.TestCase):
    """Issue #271: a bad error entry must not destroy the posts of the same run.

    `callModule` does `for source, message in errors:` *after* the module's posts
    have been collected. An entry that will not unpack into two values raised
    ValueError there, which the outer handler turned into "the module call
    failed" -- throwing away every post the module had successfully gathered.
    """

    def _consume(self, value):
        """Stand in for what callModule does with a query() return value."""
        items, errors = feedutils.split_result(value)
        logged = [f"{source}: {message}" for source, message in errors]  # must not raise
        return items, logged

    def test_bare_string_error_does_not_discard_the_posts(self):
        r = feedutils.result(items=[["news", "kept"]], errors=["everything broke"])
        items, logged = self._consume(r)
        self.assertEqual([["news", "kept"]], items)
        self.assertEqual([f"{feedutils.UNKNOWN_SOURCE}: everything broke"], logged)

    def test_wrong_arity_error_does_not_discard_the_posts(self):
        r = feedutils.result(items=[["news", "kept"]], errors=[("feed", "403", "extra")])
        items, logged = self._consume(r)
        self.assertEqual([["news", "kept"]], items)
        self.assertEqual(1, len(logged))
        # Nothing is silently dropped: both fields survive into the message.
        self.assertIn("403", logged[0])
        self.assertIn("extra", logged[0])

    def test_none_error_entry_does_not_discard_the_posts(self):
        r = feedutils.result(items=[["news", "kept"]], errors=[None])
        items, _ = self._consume(r)
        self.assertEqual([["news", "kept"]], items)

    def test_exception_object_as_error_is_stringified(self):
        r = feedutils.result(items=[], errors=[("feed", ValueError("bad payload"))])
        _, errors = feedutils.split_result(r)
        self.assertEqual([("feed", "bad payload")], errors)

    def test_hand_built_feedresult_is_normalised_too(self):
        # A module can bypass result() and construct the namedtuple directly;
        # the guarantee has to hold at the boundary callModule reads from.
        r = feedutils.FeedResult(items=[["news", "kept"]], errors=["oops"])
        items, logged = self._consume(r)
        self.assertEqual([["news", "kept"]], items)
        self.assertEqual([f"{feedutils.UNKNOWN_SOURCE}: oops"], logged)

    def test_well_formed_errors_are_untouched(self):
        r = feedutils.result(items=[], errors=[("http://x/feed", "403 blocked")])
        _, errors = feedutils.split_result(r)
        self.assertEqual([("http://x/feed", "403 blocked")], errors)


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
        # The error entry here is a well-formed (source, message) pair: result()
        # now enforces that shape at construction, so a placeholder scalar would
        # be normalised and obscure what this test is actually about.
        r = feedutils.result(items=[1], errors=[("feed", "err")])
        self.assertEqual(([1], [("feed", "err")]), (r.items, r.errors))
        # namedtuple: unpackable and indexable, so existing list-style handling
        # of a FeedResult (were one passed straight through) still degrades
        # predictably rather than raising oddly.
        items, errors = r
        self.assertEqual([1], items)
        self.assertEqual([("feed", "err")], errors)


if __name__ == "__main__":
    unittest.main()
