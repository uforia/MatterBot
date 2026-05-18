import unittest

from matterbot_formatting import defang_ioc, format_scalar, safe_markdown_cell


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


if __name__ == "__main__":
    unittest.main()
