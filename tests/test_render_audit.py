import os
import tempfile
import unittest

from render_audit import Finding, audit_modules, audit_source, format_report, main, select_vectors


class AuditSourceTests(unittest.TestCase):
    def test_flags_fence_breakout_with_interpolation(self):
        src = "reply = '\\n```%s\\n```' % (answer['content'][1:],)"
        findings = audit_source(src, "chatgpt")
        self.assertEqual(1, len(findings))
        self.assertEqual("fence", findings[0].vector)
        self.assertEqual("chatgpt", findings[0].module)
        self.assertEqual(1, findings[0].line)

    def test_flags_inline_backtick_wrap(self):
        findings = audit_source('text = f"`{value}`"', "foo")
        self.assertEqual(1, len(findings))
        self.assertEqual("inline", findings[0].vector)

    def test_flags_inline_percent_wrap(self):
        findings = audit_source("text = '`%s`' % value", "foo")
        self.assertEqual(1, len(findings))
        self.assertEqual("inline", findings[0].vector)

    def test_flags_adhoc_stripchars_idiom(self):
        findings = audit_source("stripchars = r'\\[\\]\\n\\r'", "bar")
        self.assertEqual(1, len(findings))
        self.assertEqual("adhoc-stripchars", findings[0].vector)

    def test_static_fence_without_interpolation_is_not_flagged(self):
        self.assertEqual([], audit_source("text = '```static text```'", "clean"))

    def test_benign_content_is_not_flagged(self):
        self.assertEqual([], audit_source("text = 'hello world'", "clean"))

    def test_fence_already_routed_through_sanitizer_is_not_flagged(self):
        src = "reply = '```%s```' % sanitize_block(answer)"
        self.assertEqual([], audit_source(src, "safe"))

    def test_inline_already_routed_through_sanitizer_is_not_flagged(self):
        src = 'text = f"`{sanitize_inline(value)}`"'
        self.assertEqual([], audit_source(src, "safe"))

    def test_fence_takes_precedence_over_inline_on_same_line(self):
        # A ``` line that also contains `% must report once, as a fence.
        findings = audit_source("x = '```%s```' % v", "foo")
        self.assertEqual(1, len(findings))
        self.assertEqual("fence", findings[0].vector)

    def test_reports_line_number(self):
        src = "a = 1\nb = 2\ntext = f'`{v}`'"
        findings = audit_source(src, "foo")
        self.assertEqual(3, findings[0].line)


class AuditModulesTests(unittest.TestCase):
    def test_aggregates_across_modules(self):
        items = [
            ("chatgpt", "r = '```%s```' % x"),
            ("clean", "text = 'hi'"),
            ("foo", "t = f'`{v}`'"),
        ]
        findings = audit_modules(items)
        self.assertEqual(2, len(findings))
        self.assertEqual({"chatgpt", "foo"}, {f.module for f in findings})


class FormatReportTests(unittest.TestCase):
    def test_empty_findings_report_is_clean(self):
        self.assertIn("no unsanitized render sites", format_report([]).lower())

    def test_report_groups_and_counts(self):
        findings = audit_modules([("chatgpt", "r = '```%s```' % x")])
        report = format_report(findings)
        self.assertIn("chatgpt", report)
        self.assertIn("fence", report)


class SelectVectorsTests(unittest.TestCase):
    def test_filters_to_requested_vector(self):
        findings = [
            Finding("a", 1, "fence", "x"),
            Finding("b", 2, "inline", "y"),
            Finding("c", 3, "adhoc-stripchars", "z"),
        ]
        self.assertEqual(["fence"], [f.vector for f in select_vectors(findings, ["fence"])])

    def test_keeps_multiple_requested_vectors(self):
        findings = [Finding("a", 1, "fence", "x"), Finding("b", 2, "inline", "y")]
        self.assertEqual(2, len(select_vectors(findings, ["fence", "inline"])))


class MainVectorGateTests(unittest.TestCase):
    def _write_fixture(self, root, source):
        moddir = os.path.join(root, "evilmod")
        os.makedirs(moddir)
        with open(os.path.join(moddir, "command.py"), "w", encoding="utf-8") as fh:
            fh.write(source)

    def test_fence_gate_fails_on_a_fence_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_fixture(tmp, "r = '```%s```' % x\n")
            self.assertEqual(1, main(["--root", tmp, "--check", "--vectors", "fence"]))

    def test_fence_gate_ignores_inline_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_fixture(tmp, "t = f'`{v}`'\n")
            self.assertEqual(0, main(["--root", tmp, "--check", "--vectors", "fence"]))

    def test_unknown_vector_is_rejected(self):
        with self.assertRaises(SystemExit):
            main(["--root", ".", "--check", "--vectors", "bogus"])


if __name__ == "__main__":
    unittest.main()
