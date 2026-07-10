"""Render-safety tests for the remaining fence-breakout modules (Part 4).

Each module interpolates tool/API output into a ``` fence; these assert the
output can no longer close the fence, and (where the module wraps a subject in
inline code) that the subject cannot break the inline wrap. Benign content is
preserved.
"""

import unittest

from commands.dnstwist.command import _wrap_output as dnstwist_wrap
from commands.ghunt.command import _wrap_output as ghunt_wrap
from commands.hackertarget.command import _wrap_output as hackertarget_wrap
from commands.holehe.command import _wrap_output as holehe_wrap
from commands.qualys.command import _format_api_error as qualys_error
from commands.waybacklister.command import _wrap_output as wayback_wrap

FENCE_BREAKOUT = "```\n# forged heading\n@channel click http://evil.example"


class FenceAdoptionTests(unittest.TestCase):
    def test_dnstwist_body_cannot_break_fence(self):
        out = dnstwist_wrap("registered permutations", "evil.com", FENCE_BREAKOUT, "")
        self.assertEqual(2, out.count("```"))

    def test_dnstwist_domain_cannot_break_inline(self):
        self.assertIn("`abc`", dnstwist_wrap("m", "a`b`c", "body", ""))

    def test_ghunt_body_cannot_break_fence(self):
        self.assertEqual(2, ghunt_wrap("x@y.com", FENCE_BREAKOUT).count("```"))

    def test_ghunt_email_cannot_break_inline(self):
        self.assertIn("`ab`", ghunt_wrap("a`b", "body"))

    def test_holehe_body_cannot_break_fence(self):
        self.assertEqual(2, holehe_wrap("x@y.com", FENCE_BREAKOUT).count("```"))

    def test_waybacklister_body_cannot_break_fence(self):
        self.assertEqual(2, wayback_wrap("evil.com", FENCE_BREAKOUT, "").count("```"))

    def test_hackertarget_body_cannot_break_fence(self):
        header = "**hackertarget dns** (label) for `evil.com`:"
        self.assertEqual(2, hackertarget_wrap(header, FENCE_BREAKOUT).count("```"))

    def test_qualys_fenced_content_cannot_break_fence(self):
        self.assertEqual(2, qualys_error("boom", FENCE_BREAKOUT).count("```"))

    def test_qualys_error_message_cannot_break_inline(self):
        self.assertIn("`ab`", qualys_error("a`b", "content"))

    def test_benign_content_preserved(self):
        out = ghunt_wrap("a@b.com", "clean body text")
        self.assertIn("clean body text", out)
        self.assertIn("b.com", out)


if __name__ == "__main__":
    unittest.main()
