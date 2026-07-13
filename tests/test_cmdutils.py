"""Tests for the shared command-side indicator classifier (issue #284).

`commands/cmdutils.py` decides what kind of indicator a string is, and whether a
command should run for it. The dispatcher uses these to stop a shared bind like
@ioc fanning an IP out to domain-only and hash-only modules -- each of which
would otherwise answer with an error in the channel.

Stdlib-only, like the module under test, so it runs under the dependency-free
`python -m unittest` CI runner.
"""

import sys
import unittest
from pathlib import Path

# cmdutils lives in commands/, which is not on the path under the test runner.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "commands"))

import cmdutils


class ClassifyTests(unittest.TestCase):
    def _type(self, value):
        return cmdutils.classify(value)[1]

    def test_ipv4(self):
        self.assertEqual('ip', self._type('8.8.8.8'))

    def test_ipv6(self):
        self.assertEqual('ipv6', self._type('2001:4860:4860::8888'))

    def test_domain(self):
        self.assertEqual('domain', self._type('evil.example.com'))

    def test_url(self):
        self.assertEqual('url', self._type('https://evil.example.com/a?b=c'))

    def test_md5_sha1_sha256(self):
        self.assertEqual('md5', self._type('d41d8cd98f00b204e9800998ecf8427e'))
        self.assertEqual('sha1', self._type('a' * 40))
        self.assertEqual('sha256', self._type('a' * 64))

    def test_cidr_ranges(self):
        self.assertEqual('cidr', self._type('10.0.0.0/8'))
        self.assertEqual('cidr', self._type('2001:db8::/32'))
        # A prefix written with host bits set is still a range, not an address.
        self.assertEqual('cidr', self._type('8.8.8.8/24'))

    def test_bare_address_is_not_a_cidr(self):
        # The distinction the separate type exists for: a single address must
        # stay ip/ipv6 so it does not route to netblock-only lookups.
        self.assertEqual('ip', self._type('8.8.8.8'))
        self.assertEqual('ipv6', self._type('2001:db8::1'))

    def test_number_and_partial_ip_are_not_cidr(self):
        # ip_network is lenient; make sure it does not swallow non-ranges.
        self.assertIsNone(self._type('32'))
        self.assertIsNone(self._type('1.2.3'))
        self.assertIsNone(self._type('evil.com/24'))

    def test_non_indicator_is_none(self):
        self.assertIsNone(self._type('notanindicator'))
        self.assertIsNone(self._type('some free text query'))

    def test_empty_and_none_are_none(self):
        self.assertIsNone(self._type(''))
        self.assertIsNone(self._type('   '))
        self.assertIsNone(cmdutils.classify(None)[1])

    def test_hash_wins_over_domain_shaped_confusion(self):
        # A 64-char hex string is a SHA256, never a (bizarre) hostname.
        self.assertEqual('sha256', self._type('deadbeef' * 8))

    def test_normalises_case_and_whitespace(self):
        value, itype = cmdutils.classify('  D41D8CD98F00B204E9800998ECF8427E  ')
        self.assertEqual('md5', itype)
        self.assertEqual('d41d8cd98f00b204e9800998ecf8427e', value)

    def test_refangs_defanged_indicators(self):
        # Threat-intel indicators are shared defanged; a pasted one is the
        # indicator, not a typo.
        self.assertEqual(('8.8.8.8', 'ip'), cmdutils.classify('8[.]8[.]8[.]8'))
        self.assertEqual('url', cmdutils.classify('hxxp://bad[.]com/x')[1])
        self.assertEqual('domain', cmdutils.classify('bad[.]com')[1])

    def test_every_returned_type_is_in_the_vocabulary(self):
        for value in ['8.8.8.8', '::1', 'a.io', 'http://a.io', 'a' * 32, 'a' * 40, 'a' * 64]:
            self.assertIn(cmdutils.classify(value)[1], cmdutils.TYPES)


class AcceptsTests(unittest.TestCase):
    def test_no_declaration_accepts_anything(self):
        # Backwards compatibility: an un-annotated command runs as before.
        self.assertTrue(cmdutils.accepts({}, 'ip'))
        self.assertTrue(cmdutils.accepts({'accepts': None}, 'domain'))
        self.assertTrue(cmdutils.accepts({}, None))

    def test_declared_type_matches(self):
        self.assertTrue(cmdutils.accepts({'accepts': ['ip', 'ipv6']}, 'ip'))

    def test_declared_type_excludes_others(self):
        self.assertFalse(cmdutils.accepts({'accepts': ['domain']}, 'ip'))

    def test_declared_command_skips_unclassifiable_input(self):
        # None must not match a type-aware command -- that is what keeps junk
        # input from reaching a module that declared what it accepts.
        self.assertFalse(cmdutils.accepts({'accepts': ['ip']}, None))


class NormaliseAcceptsTests(unittest.TestCase):
    def test_valid_list_passes_through_known_types(self):
        self.assertEqual(['ip', 'domain'], cmdutils.normalise_accepts(['ip', 'domain']))

    def test_unknown_types_are_dropped(self):
        # A typo like 'ipv4' must not create a rule that can never match.
        self.assertEqual(['ip'], cmdutils.normalise_accepts(['ip', 'ipv4', 'bogus']))

    def test_all_unknown_becomes_none_not_empty(self):
        # An all-garbage ACCEPTS becomes accept-anything, not accept-nothing;
        # accept-nothing would make the module silently dead.
        self.assertIsNone(cmdutils.normalise_accepts(['ipv4', 'bogus']))

    def test_non_list_becomes_none(self):
        self.assertIsNone(cmdutils.normalise_accepts('ip'))
        self.assertIsNone(cmdutils.normalise_accepts(None))
        self.assertIsNone(cmdutils.normalise_accepts([]))


class RoutingBehaviourTests(unittest.TestCase):
    """Exercise the dispatch decision the way matterbot.py does, on the real
    ACCEPTS declared by the starter-set modules -- classify the arg, then keep
    only the modules that accept it."""

    # Mirrors the three modules annotated in this change.
    COMMANDS = {
        'crtsh':    {'accepts': ['domain']},
        'malshare': {'accepts': ['md5', 'sha1', 'sha256']},
        'ipinfo':   {'accepts': ['ip', 'ipv6']},
        'legacy':   {},  # un-annotated: must still run for everything
    }

    def _route(self, arg):
        _, itype = cmdutils.classify(arg)
        return sorted(m for m, entry in self.COMMANDS.items()
                      if cmdutils.accepts(entry, itype))

    def test_ip_routes_to_ip_module_and_legacy_only(self):
        self.assertEqual(['ipinfo', 'legacy'], self._route('8.8.8.8'))

    def test_domain_routes_to_domain_module_and_legacy_only(self):
        self.assertEqual(['crtsh', 'legacy'], self._route('evil.example.com'))

    def test_hash_routes_to_hash_module_and_legacy_only(self):
        self.assertEqual(['legacy', 'malshare'], self._route('a' * 64))

    def test_junk_routes_to_legacy_only(self):
        # notanindicator classifies to None: type-aware modules all drop out,
        # only the un-annotated one remains. Once the whole @ioc set is
        # annotated, this becomes empty -> the dispatcher's no-match reply.
        self.assertEqual(['legacy'], self._route('notanindicator'))

    def test_ip_module_is_not_called_for_a_domain(self):
        self.assertNotIn('ipinfo', self._route('evil.example.com'))

    def test_domain_module_is_not_called_for_an_ip(self):
        self.assertNotIn('crtsh', self._route('8.8.8.8'))


class ShippedAcceptsTests(unittest.TestCase):
    """Assert routing invariants against the ACCEPTS actually declared in the
    command defaults, so a bad edit to a real module is caught -- not a copy of
    the values kept in this test.
    """

    COMMANDS_DIR = Path(__file__).resolve().parent.parent / "commands"

    def _accepts(self, module):
        import ast
        src = (self.COMMANDS_DIR / module / "defaults.py").read_text(encoding="utf-8")
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ACCEPTS" for t in node.targets
            ):
                return ast.literal_eval(node.value)
        return None

    def _routes_to(self, module, value):
        entry = {'accepts': cmdutils.normalise_accepts(self._accepts(module))}
        _, itype = cmdutils.classify(value)
        return cmdutils.accepts(entry, itype)

    def test_every_declared_accepts_is_valid(self):
        # A typo would be normalised away; declared and normalised must agree, or
        # the module would silently accept more (or fewer) types than intended.
        for module in ['bssc', 'honeydb', 'ipwhois', 'malwarebazaar', 'ripewhois',
                       'sslmate', 'threatbook', 'threatfox', 'threatrip', 'urlhaus',
                       'wayback', 'crtsh', 'malshare', 'ipinfo',
                       'abuseipdb', 'circlpdns']:
            declared = self._accepts(module)
            self.assertIsNotNone(declared, f"{module} lost its ACCEPTS")
            self.assertEqual(declared, cmdutils.normalise_accepts(declared),
                             f"{module} ACCEPTS has an unknown/typo'd type")

    def test_hash_only_modules_reject_ip_and_domain(self):
        for module in ['malwarebazaar', 'malshare']:
            self.assertFalse(self._routes_to(module, '8.8.8.8'))
            self.assertFalse(self._routes_to(module, 'evil.com'))
            self.assertTrue(self._routes_to(module, 'a' * 64))

    def test_ipv4_only_modules_are_not_called_for_ipv6(self):
        # ipwhois/ripewhois/threatfox validate with a v4 regex; a v6 indicator
        # must not route to them (they would reject it).
        for module in ['ipwhois', 'ripewhois', 'threatfox']:
            self.assertTrue(self._routes_to(module, '8.8.8.8'))
            self.assertFalse(self._routes_to(module, '2001:db8::1'))

    def test_honeydb_handles_ipv6(self):
        # honeydb validates with ipaddress, so it does take v6 -- and must route.
        self.assertTrue(self._routes_to('honeydb', '2001:db8::1'))

    def test_wayback_is_url_only(self):
        self.assertTrue(self._routes_to('wayback', 'http://evil.com/x'))
        self.assertFalse(self._routes_to('wayback', 'evil.com'))
        self.assertFalse(self._routes_to('wayback', '8.8.8.8'))

    def test_netblock_modules_take_cidr_and_single_addresses(self):
        for module in ['abuseipdb', 'circlpdns']:
            self.assertTrue(self._routes_to(module, '10.0.0.0/8'))
            self.assertTrue(self._routes_to(module, '8.8.8.8'))
            self.assertTrue(self._routes_to(module, '2001:db8::/32'))

    def test_single_address_modules_do_not_take_cidr(self):
        # honeydb/ipinfo look up one address; a range must not route to them.
        for module in ['honeydb', 'ipinfo']:
            self.assertTrue(self._routes_to(module, '8.8.8.8'))
            self.assertFalse(self._routes_to(module, '10.0.0.0/8'))

    def test_circlpdns_takes_domains_abuseipdb_does_not(self):
        self.assertTrue(self._routes_to('circlpdns', 'evil.com'))
        self.assertFalse(self._routes_to('abuseipdb', 'evil.com'))


if __name__ == "__main__":
    unittest.main()
