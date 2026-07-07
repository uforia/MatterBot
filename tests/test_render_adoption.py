"""Render-safety tests for command modules that adopted the sanitize_* helpers.

These assert the specific Markdown-injection vectors render_audit flagged for
each module can no longer break out, while benign content is preserved.
"""

import unittest

from commands.chatgpt.command import _format_answer, _format_error
from commands.unfurl.command import _format_tree


class ChatgptRenderTests(unittest.TestCase):
    def test_model_output_cannot_break_out_of_fence(self):
        out = _format_answer("```\n@channel escaped the code block")
        # Only the wrapper's own opening + closing fence should remain.
        self.assertEqual(2, out.count("```"))

    def test_error_message_cannot_break_inline_code(self):
        out = _format_error("boom `injected` payload")
        self.assertIn("`boom injected payload`", out)

    def test_benign_answer_is_preserved(self):
        self.assertIn("hello world", _format_answer("hello world"))


class UnfurlRenderTests(unittest.TestCase):
    def test_tool_output_cannot_break_out_of_fence(self):
        out = _format_tree("http://example.com", "```\nmalicious payload")
        self.assertEqual(2, out.count("```"))

    def test_url_cannot_break_inline_code(self):
        out = _format_tree("a`b`c", "tree")
        self.assertIn("`abc`", out)

    def test_benign_tree_is_preserved(self):
        out = _format_tree("http://example.com", "scheme: http")
        self.assertIn("scheme: http", out)
        self.assertIn("example.com", out)


if __name__ == "__main__":
    unittest.main()
