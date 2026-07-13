"""Tests for the conversational AI analyst (ai_analyst.py).

Stdlib-only, with a stubbed LLM client and a stubbed tool executor, so the whole
agent loop runs under the dependency-free `python -m unittest` CI runner with no
network. ai_analyst.py must therefore never import `requests` at module top --
the LLM client imports it lazily.
"""

import sys
import unittest
from pathlib import Path

# ai_analyst.py lives at the repo root and imports `commands.cmdutils` as a
# namespace package, so the repo root is what has to be on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai_analyst


class ExtractIndicatorsTests(unittest.TestCase):
    def test_extracts_indicators_from_prose(self):
        found = ai_analyst.extract_indicators(
            "we're seeing beacons to 8.8.8.8 and a dropped file "
            "d41d8cd98f00b204e9800998ecf8427e, thoughts?"
        )
        self.assertEqual(found, {'8.8.8.8': 'ip', 'd41d8cd98f00b204e9800998ecf8427e': 'md5'})

    def test_refangs_and_strips_wrapping_punctuation(self):
        found = ai_analyst.extract_indicators("check `evil.example.com`, and 8.8.8[.]8.")
        self.assertEqual(found, {'evil.example.com': 'domain', '8.8.8.8': 'ip'})

    def test_comma_separated_indicators_with_no_spaces(self):
        # Analysts paste straight out of a spreadsheet.
        found = ai_analyst.extract_indicators("8.8.8.8,evil.example.com;1.1.1.1")
        self.assertEqual(
            found, {'8.8.8.8': 'ip', 'evil.example.com': 'domain', '1.1.1.1': 'ip'}
        )

    def test_labelled_indicators(self):
        found = ai_analyst.extract_indicators("IOC:evil.example.com and ip=8.8.8.8")
        self.assertEqual(found, {'evil.example.com': 'domain', '8.8.8.8': 'ip'})

    def test_markdown_links_yield_both_label_and_target(self):
        found = ai_analyst.extract_indicators(
            "[evil.example.com](https://evil.example.com/path)"
        )
        self.assertEqual(found['evil.example.com'], 'domain')
        self.assertEqual(found['https://evil.example.com/path'], 'url')

    def test_defanged_url_with_a_path(self):
        found = ai_analyst.extract_indicators("hxxps://evil[.]example[.]com/path?x=y")
        self.assertEqual(found, {'https://evil.example.com/path?x=y': 'url'})

    def test_bare_host_with_a_path_still_yields_the_domain(self):
        # No scheme, so it is not a URL -- but the host is still an indicator.
        found = ai_analyst.extract_indicators("evil[.]example[.]com/path")
        self.assertEqual(found, {'evil.example.com': 'domain'})

    def test_prose_with_no_indicators_is_empty(self):
        self.assertEqual(ai_analyst.extract_indicators("what do you make of this?"), {})
        self.assertEqual(ai_analyst.extract_indicators(""), {})
        self.assertEqual(ai_analyst.extract_indicators(None), {})


class SanitizeToolOutputTests(unittest.TestCase):
    """Module output now leaves the host for a third-party LLM. Redact it."""

    def test_redacts_query_string_credentials(self):
        raw = "https://api.example.test/search?key=SECRET123456&query=8.8.8.8"
        out = ai_analyst.sanitize_tool_output(raw)
        self.assertNotIn('SECRET123456', out)
        self.assertIn('8.8.8.8', out, 'redaction must not destroy the evidence')

    def test_redacts_labelled_secrets(self):
        for raw in (
            "api_key: NOTAREALKEY0001",
            "apikey=NOTAREALKEY0001",
            "access_token: NOTAREALKEY0001",
            "password = hunter2hunter2",
        ):
            self.assertNotIn('NOTAREALKEY0001', ai_analyst.sanitize_tool_output(raw), raw)
            self.assertNotIn('hunter2hunter2', ai_analyst.sanitize_tool_output(raw), raw)

    def test_redacts_bearer_tokens(self):
        out = ai_analyst.sanitize_tool_output("Authorization: Bearer NOTAREALTOKEN003")
        self.assertNotIn('NOTAREALTOKEN003', out)

    def test_leaves_ordinary_evidence_alone(self):
        raw = "| Domain | Verdict |\n|---|---|\n| evil.example.com | malicious |"
        self.assertEqual(ai_analyst.sanitize_tool_output(raw), raw)

    def test_handles_empty_input(self):
        self.assertEqual(ai_analyst.sanitize_tool_output(''), '')
        self.assertIsNone(ai_analyst.sanitize_tool_output(None))


def _registry():
    """A fake command registry in the shape matterbot.py's self.commands has."""
    return {
        'crtsh': {
            'binds': ['@crtsh', '@ioc'],
            'accepts': ['domain'],
            'help': {'DEFAULT': {'desc': 'Query crt.sh for certificates.'}},
            'aitool': True,
        },
        'circlpdns': {
            'binds': ['@circlpdns', '@ioc'],
            'accepts': ['ip', 'ipv6', 'cidr', 'domain'],
            'help': {'DEFAULT': {'desc': 'Query CIRCL passive DNS.'}},
            'aitool': True,
        },
        'malwarebazaar': {
            'binds': ['@mb', '@ioc'],
            'accepts': ['md5', 'sha1', 'sha256'],
            'help': {'DEFAULT': {'desc': 'Query MalwareBazaar for a sample.'}},
            'aitool': True,
        },
        'diceroll': {
            'binds': ['@roll'],
            'accepts': None,
            'help': {'DEFAULT': {'desc': 'Roll dice.'}},
            'aitool': False,
        },
    }


class ToolDefinitionTests(unittest.TestCase):
    def test_only_aitool_modules_are_exposed(self):
        tools = ai_analyst.build_tool_definitions(_registry(), {'domain', 'md5'})
        names = {t['function']['name'] for t in tools}
        self.assertEqual(names, {'crtsh', 'circlpdns', 'malwarebazaar'})
        self.assertNotIn('diceroll', names)

    def test_exposure_is_narrowed_to_the_relevant_indicator_types(self):
        tools = ai_analyst.build_tool_definitions(_registry(), {'md5'})
        self.assertEqual({t['function']['name'] for t in tools}, {'malwarebazaar'})

    def test_no_indicators_means_no_tools(self):
        self.assertEqual(ai_analyst.build_tool_definitions(_registry(), set()), [])

    def test_schema_is_generated_from_existing_metadata(self):
        tools = ai_analyst.build_tool_definitions(_registry(), {'domain'})
        fn = [t for t in tools if t['function']['name'] == 'crtsh'][0]['function']
        self.assertIn('Query crt.sh for certificates.', fn['description'])
        self.assertIn('domain', fn['description'])
        self.assertEqual(fn['parameters']['required'], ['query'])
        self.assertEqual(fn['parameters']['properties']['query']['type'], 'string')

    def test_module_without_help_still_produces_a_tool(self):
        registry = {'nohelp': {'binds': ['@nohelp'], 'accepts': ['ip'], 'help': {}, 'aitool': True}}
        tools = ai_analyst.build_tool_definitions(registry, {'ip'})
        self.assertEqual(len(tools), 1)
        self.assertIn('ip', tools[0]['function']['description'])


if __name__ == "__main__":
    unittest.main()
