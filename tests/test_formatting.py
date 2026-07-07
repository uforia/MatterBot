import unittest

from matterbot_formatting import (
    defang_ioc,
    format_scalar,
    safe_markdown_cell,
    sanitize_block,
    sanitize_blockquote,
    sanitize_heading_echo,
    sanitize_inline,
)


class DefangIocTests(unittest.TestCase):
    def test_defangs_domain_name(self):
        self.assertEqual("example[.]com", defang_ioc("example.com", "domain-name"))

    def test_defangs_ipv4(self):
        self.assertEqual("1[.]2.3.4", defang_ioc("1.2.3.4", "ipv4-addr"))

    def test_defangs_url_scheme_and_first_dot(self):
        self.assertEqual("hxxps://example[.]com/a", defang_ioc("https://example.com/a", "url"))

    def test_unknown_type_passes_through_as_string(self):
        self.assertEqual("example.com", defang_ioc("example.com", "x-example"))

    def test_none_becomes_empty_string(self):
        self.assertEqual("", defang_ioc(None, "domain-name"))


class MarkdownFormattingTests(unittest.TestCase):
    def test_safe_markdown_cell_escapes_table_delimiter(self):
        self.assertEqual("a\\|b", safe_markdown_cell("a|b"))

    def test_safe_markdown_cell_collapses_newlines(self):
        self.assertEqual("a b", safe_markdown_cell("a\nb"))

    def test_safe_markdown_cell_handles_none(self):
        self.assertEqual("", safe_markdown_cell(None))

    def test_format_scalar_wraps_values_in_backticks(self):
        self.assertEqual("`abc`", format_scalar("abc"))

    def test_format_scalar_empty_value_is_dash(self):
        self.assertEqual("-", format_scalar(""))

    def test_format_scalar_defangs_before_formatting(self):
        self.assertEqual("`example[.]com`", format_scalar("example.com", "domain-name"))


class SanitizeInlineTests(unittest.TestCase):
    def test_strips_backticks_so_inline_wrap_cannot_break(self):
        self.assertEqual("abc", sanitize_inline("a`b`c"))

    def test_collapses_newlines(self):
        self.assertEqual("a b", sanitize_inline("a\nb"))

    def test_none_becomes_empty_string(self):
        self.assertEqual("", sanitize_inline(None))

    def test_benign_text_unchanged(self):
        self.assertEqual("hello world", sanitize_inline("hello world"))


class SanitizeBlockTests(unittest.TestCase):
    def test_neutralizes_fence_breakout(self):
        out = sanitize_block("```py\nevil\n```")
        self.assertNotIn("```", out)

    def test_preserves_visible_backtick_count(self):
        self.assertEqual(3, sanitize_block("```").count("`"))

    def test_single_backtick_unchanged(self):
        self.assertEqual("a`b", sanitize_block("a`b"))

    def test_none_becomes_empty_string(self):
        self.assertEqual("", sanitize_block(None))


class SanitizeBlockquoteTests(unittest.TestCase):
    def test_escapes_leading_gt(self):
        self.assertEqual("\\> forged quote", sanitize_blockquote("> forged quote"))

    def test_escapes_leading_gt_per_line(self):
        self.assertEqual("a\n\\> b", sanitize_blockquote("a\n> b"))

    def test_preserves_indent_before_escaped_gt(self):
        self.assertEqual("  \\> x", sanitize_blockquote("  > x"))

    def test_benign_text_unchanged(self):
        self.assertEqual("not a quote", sanitize_blockquote("not a quote"))

    def test_none_becomes_empty_string(self):
        self.assertEqual("", sanitize_blockquote(None))


class SanitizeHeadingEchoTests(unittest.TestCase):
    def test_escapes_leading_hash(self):
        self.assertEqual("\\# forged heading", sanitize_heading_echo("# forged heading"))

    def test_escapes_leading_gt(self):
        self.assertEqual("\\> forged", sanitize_heading_echo("> forged"))

    def test_collapses_newlines_to_single_line(self):
        self.assertEqual("a b", sanitize_heading_echo("a\nb"))

    def test_benign_text_unchanged(self):
        self.assertEqual("query result", sanitize_heading_echo("query result"))

    def test_none_becomes_empty_string(self):
        self.assertEqual("", sanitize_heading_echo(None))


if __name__ == "__main__":
    unittest.main()
