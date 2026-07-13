"""Tests for the conversational AI analyst (ai_analyst.py).

Stdlib-only, with a stubbed LLM client and a stubbed tool executor, so the whole
agent loop runs under the dependency-free `python -m unittest` CI runner with no
network. ai_analyst.py must therefore never import `requests` at module top --
the LLM client imports it lazily.
"""

import json
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

    # -- Bug 1: ordinary prose must not be misread as a domain (#task-3 review) --

    def test_run_together_sentence_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("checked it.Then rebooted")
        self.assertEqual(found, {})

    def test_doc_filename_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("report.doc is attached")
        self.assertEqual(found, {})

    def test_exe_filename_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("the file malware.exe")
        self.assertEqual(found, {})

    def test_log_filename_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("error.log shows failures")
        self.assertEqual(found, {})

    def test_py_filename_is_not_a_domain(self):
        # .py collides with a real 2-letter ccTLD (Paraguay) -- the blocklist
        # must win over the generic ccTLD accept-rule.
        found = ai_analyst.extract_indicators("run config.py to reproduce")
        self.assertEqual(found, {})

    def test_sh_filename_is_not_a_domain(self):
        # .sh collides with Saint Helena's ccTLD.
        found = ai_analyst.extract_indicators("kick off deploy.sh first")
        self.assertEqual(found, {})

    def test_md_filename_is_not_a_domain(self):
        # .md collides with Moldova's ccTLD.
        found = ai_analyst.extract_indicators("see notes.md for context")
        self.assertEqual(found, {})

    def test_db_filename_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("restore backup.db from last night")
        self.assertEqual(found, {})

    # -- Bug 2: joined indicator pairs must not silently drop the second value --

    def test_slash_joined_ip_pair_yields_both(self):
        found = ai_analyst.extract_indicators("8.8.8.8/1.1.1.1")
        self.assertEqual(found, {'8.8.8.8': 'ip', '1.1.1.1': 'ip'})

    def test_arrow_joined_ip_pair_yields_both(self):
        found = ai_analyst.extract_indicators("8.8.8.8->1.1.1.1")
        self.assertEqual(found, {'8.8.8.8': 'ip', '1.1.1.1': 'ip'})

    # -- Bug 3: a token that already classifies must not be dismantled further --

    def test_cidr_is_not_dismantled_into_a_bare_ip(self):
        found = ai_analyst.extract_indicators("10.0.0.0/8 is ours")
        self.assertEqual(found, {'10.0.0.0/8': 'cidr'})

    # -- Regression coverage: legitimate indicators must still classify --

    def test_plain_domain_still_classifies(self):
        found = ai_analyst.extract_indicators("evil.example.com")
        self.assertEqual(found, {'evil.example.com': 'domain'})

    def test_plain_ip_still_classifies(self):
        found = ai_analyst.extract_indicators("8.8.8.8")
        self.assertEqual(found, {'8.8.8.8': 'ip'})

    def test_defanged_domain_still_classifies(self):
        found = ai_analyst.extract_indicators("evil[.]example[.]com")
        self.assertEqual(found, {'evil.example.com': 'domain'})

    def test_real_malware_tld_ml_still_classifies(self):
        found = ai_analyst.extract_indicators("bad.ml")
        self.assertEqual(found, {'bad.ml': 'domain'})

    def test_real_malware_tld_xyz_still_classifies(self):
        found = ai_analyst.extract_indicators("evil.xyz")
        self.assertEqual(found, {'evil.xyz': 'domain'})

    def test_defanged_domain_in_a_weird_tld_survives_the_gate(self):
        # Not in any TLD table this module knows about -- but the analyst
        # defanged it, which is a statement of intent that must win.
        found = ai_analyst.extract_indicators("phish[.]notarealtld")
        self.assertEqual(found, {'phish.notarealtld': 'domain'})

    def test_labelled_domain_in_a_weird_tld_survives_the_gate(self):
        found = ai_analyst.extract_indicators("domain=sketchy.notarealtld")
        self.assertEqual(found, {'sketchy.notarealtld': 'domain'})

    def test_markdown_link_case_still_works(self):
        found = ai_analyst.extract_indicators(
            "[evil.example.com](https://evil.example.com/path)"
        )
        self.assertEqual(found['evil.example.com'], 'domain')
        self.assertEqual(found['https://evil.example.com/path'], 'url')

    def test_defanged_url_with_path_case_still_works(self):
        found = ai_analyst.extract_indicators("hxxps://evil[.]example[.]com/path?x=y")
        self.assertEqual(found, {'https://evil.example.com/path?x=y': 'url'})

    # -- Task 3: abuse-heavy gTLDs that were previously rejected --
    # Missed real IOCs are the worst failure mode. Added to the allowlist:
    # monster, download, security, and related abuse-prone gTLDs.

    def test_monster_tld_domain_classifies(self):
        # .monster is a real abuse-heavy gTLD used in phishing campaigns.
        found = ai_analyst.extract_indicators("b.monster")
        self.assertEqual(found, {'b.monster': 'domain'})

    def test_download_tld_domain_classifies(self):
        # .download is a real abuse-heavy gTLD used in malware delivery.
        found = ai_analyst.extract_indicators("e.download")
        self.assertEqual(found, {'e.download': 'domain'})

    def test_security_tld_domain_classifies(self):
        # .security is a real abuse-heavy gTLD.
        found = ai_analyst.extract_indicators("c2.security")
        self.assertEqual(found, {'c2.security': 'domain'})

    def test_stream_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.stream")
        self.assertEqual(found, {'evil.stream': 'domain'})

    def test_review_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("phish.review")
        self.assertEqual(found, {'phish.review': 'domain'})

    # -- Regression: file extensions must remain blocked --
    # .zip and .mov collide with extremely common filenames (payload.zip, clip.mov)
    # and must stay blocked. Analysts can defang or label them to bypass the gate.

    def test_zip_filename_remains_blocked(self):
        # Bare .zip must NOT be treated as a domain (too common: payload.zip).
        # Defanging rescues the genuine domain case: evil[.]zip -> 'domain'
        found = ai_analyst.extract_indicators("payload.zip is the sample")
        self.assertEqual(found, {})

    def test_mov_filename_remains_blocked(self):
        # Bare .mov must NOT be treated as a domain (too common: clip.mov).
        # Defanging rescues the genuine domain case: video[.]mov -> 'domain'
        found = ai_analyst.extract_indicators("clip.mov was extracted")
        self.assertEqual(found, {})

    def test_defanged_zip_domain_survives_the_gate(self):
        # Even though .zip is blocklisted, defanging signals analyst intent.
        found = ai_analyst.extract_indicators("evil[.]zip")
        self.assertEqual(found, {'evil.zip': 'domain'})

    def test_labelled_zip_domain_survives_the_gate(self):
        # Labelling also signals analyst intent.
        found = ai_analyst.extract_indicators("domain=malicious.zip")
        self.assertEqual(found, {'malicious.zip': 'domain'})

    # -- Task 3 (review round 2): a hand-curated TLD list cannot win against
    # ~1450 real delegated TLDs. These are real IANA TLDs that a curated list
    # missed -- and a reviewer showed each one is silently dropped, bare, in
    # prose, with nothing anywhere saying so. The fix replaces the curated list
    # with the authoritative IANA set, so membership -- not a hand-picked
    # table -- decides plausibility.

    def test_bond_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("seeing beacons to c2.bond, thoughts?")
        self.assertEqual(found, {'c2.bond': 'domain'})

    def test_gdn_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.gdn")
        self.assertEqual(found, {'evil.gdn': 'domain'})

    def test_surf_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.surf")
        self.assertEqual(found, {'evil.surf': 'domain'})

    def test_kim_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.kim")
        self.assertEqual(found, {'evil.kim': 'domain'})

    def test_mom_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("phish.mom")
        self.assertEqual(found, {'phish.mom': 'domain'})

    def test_wang_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("c2.wang")
        self.assertEqual(found, {'c2.wang': 'domain'})

    def test_moe_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("c2.moe")
        self.assertEqual(found, {'c2.moe': 'domain'})

    def test_ninja_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("c2.ninja")
        self.assertEqual(found, {'c2.ninja': 'domain'})

    def test_wtf_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("c2.wtf")
        self.assertEqual(found, {'c2.wtf': 'domain'})

    def test_zone_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.zone")
        self.assertEqual(found, {'evil.zone': 'domain'})

    def test_ltd_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.ltd")
        self.assertEqual(found, {'evil.ltd': 'domain'})

    def test_center_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.center")
        self.assertEqual(found, {'evil.center': 'domain'})

    def test_fund_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("c2.fund")
        self.assertEqual(found, {'c2.fund': 'domain'})

    def test_ceo_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.ceo")
        self.assertEqual(found, {'evil.ceo': 'domain'})

    def test_exposed_tld_domain_classifies(self):
        found = ai_analyst.extract_indicators("evil.exposed")
        self.assertEqual(found, {'evil.exposed': 'domain'})

    # -- Prose false positives must still reject: none of these are real TLDs --

    def test_yml_extension_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("config.yml has the settings")
        self.assertEqual(found, {})

    def test_passwd_file_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("check etc.passwd for the hash")
        self.assertEqual(found, {})

    def test_help_desk_prose_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("open a help.desk ticket")
        self.assertEqual(found, {})

    def test_oauth_token_prose_is_not_a_domain(self):
        found = ai_analyst.extract_indicators("refresh the oauth.token before retrying")
        self.assertEqual(found, {})

    # -- Removing the 2-letter-ccTLD escape hatch must not reopen these --

    def test_py_filename_remains_blocked_bare(self):
        found = ai_analyst.extract_indicators("run script.py to reproduce")
        self.assertEqual(found, {})

    def test_sh_filename_remains_blocked_bare(self):
        found = ai_analyst.extract_indicators("kick off run.sh first")
        self.assertEqual(found, {})

    def test_defanged_mov_domain_survives_the_gate(self):
        found = ai_analyst.extract_indicators("evil[.]mov")
        self.assertEqual(found, {'evil.mov': 'domain'})

    def test_defanged_py_domain_survives_the_gate(self):
        found = ai_analyst.extract_indicators("bad[.]py")
        self.assertEqual(found, {'bad.py': 'domain'})

    # -- Regression: real domains, IPs, CIDRs still behave --

    def test_tk_tld_domain_still_classifies(self):
        found = ai_analyst.extract_indicators("phish.tk")
        self.assertEqual(found, {'phish.tk': 'domain'})

    def test_multi_label_cctld_still_classifies(self):
        found = ai_analyst.extract_indicators("host.co.uk")
        self.assertEqual(found, {'host.co.uk': 'domain'})

    def test_punycode_domain_still_classifies(self):
        found = ai_analyst.extract_indicators("xn--80ak6aa92e.com")
        self.assertEqual(found, {'xn--80ak6aa92e.com': 'domain'})

    def test_bare_ip_still_classifies(self):
        found = ai_analyst.extract_indicators("8.8.8.8")
        self.assertEqual(found, {'8.8.8.8': 'ip'})

    def test_cidr_only_not_bare_ip(self):
        found = ai_analyst.extract_indicators("10.0.0.0/8")
        self.assertEqual(found, {'10.0.0.0/8': 'cidr'})

    def test_two_ips_arrow_joined_still_both_yielded(self):
        found = ai_analyst.extract_indicators("8.8.8.8->1.1.1.1")
        self.assertEqual(found, {'8.8.8.8': 'ip', '1.1.1.1': 'ip'})

    def test_defanged_url_with_path_still_classifies(self):
        found = ai_analyst.extract_indicators("hxxps://evil[.]example[.]com/path?x=y")
        self.assertEqual(found, {'https://evil.example.com/path?x=y': 'url'})


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


BOT = 'bot-id'
HUMAN = 'human-id'


def _user(message):
    return {'user_id': HUMAN, 'message': message, 'props': {}}


def _reply(message, tool_calls=0, msg_id='m1', part=0):
    return {
        'user_id': BOT,
        'message': message,
        'props': {
            ai_analyst.PROP_KEY: ai_analyst.PROP_REPLY,
            ai_analyst.PROP_TOOL_CALLS: tool_calls,
            ai_analyst.PROP_MSG_ID: msg_id,
            ai_analyst.PROP_PART: part,
        },
    }


def _evidence(message):
    return {
        'user_id': BOT, 'message': message,
        'props': {ai_analyst.PROP_KEY: ai_analyst.PROP_EVIDENCE},
    }


def _reconstruct(posts, default_mode='compact', max_history_turns=20):
    return ai_analyst.reconstruct(posts, BOT, default_mode, max_history_turns, '@ai')


class NormaliseThreadTests(unittest.TestCase):
    """The exact shape mmDriver.posts.get_thread() returns."""

    def test_orders_by_create_at_and_drops_the_current_post(self):
        payload = {
            'order': ['p2', 'p1'],
            'posts': {
                'p2': {'id': 'p2', 'create_at': 200, 'message': 'second'},
                'p1': {'id': 'p1', 'create_at': 100, 'message': 'first'},
                'p3': {'id': 'p3', 'create_at': 300, 'message': 'current'},
            },
        }
        posts = ai_analyst.normalise_thread(payload, exclude_post_id='p3')
        self.assertEqual([p['id'] for p in posts], ['p1', 'p2'])

    def test_empty_or_missing_payload_is_empty(self):
        self.assertEqual(ai_analyst.normalise_thread(None, None), [])
        self.assertEqual(ai_analyst.normalise_thread({}, None), [])

    # -- Bug (review finding #1): split-reply parts must rejoin in SEND order,
    # not id order (#task-4 review) --

    def test_orders_split_reply_parts_by_ai_part_not_id(self):
        # send_message() posts every part of a split reply back-to-back, so
        # create_at (millisecond resolution) routinely TIES between two
        # parts. Here both parts share create_at=1000 and the post ids sort
        # BACKWARDS relative to send order ('b7m3' < ... no, 'b7m3' > 'xk2n'
        # is false too -- the point is id order must simply not matter: only
        # ai_part may break the tie).
        payload = {
            'posts': {
                'b7m3n': {'id': 'b7m3n', 'create_at': 1000, 'message': 'second', 'props': {'ai_part': 1}},
                'xk2np': {'id': 'xk2np', 'create_at': 1000, 'message': 'first', 'props': {'ai_part': 0}},
            },
        }
        posts = ai_analyst.normalise_thread(payload)
        self.assertEqual([p['id'] for p in posts], ['xk2np', 'b7m3n'])

    def test_ai_part_beats_id_even_when_id_sorts_the_opposite_way(self):
        # Same as above but with the id ordering flipped, to prove the sort
        # is not accidentally still keying off id.
        payload = {
            'posts': {
                'aaa': {'id': 'aaa', 'create_at': 5000, 'message': 'second', 'props': {'ai_part': 1}},
                'zzz': {'id': 'zzz', 'create_at': 5000, 'message': 'first', 'props': {'ai_part': 0}},
            },
        }
        posts = ai_analyst.normalise_thread(payload)
        self.assertEqual([p['id'] for p in posts], ['zzz', 'aaa'])

    def test_missing_or_invalid_ai_part_does_not_crash_and_reads_as_zero(self):
        payload = {
            'posts': {
                'a': {'id': 'a', 'create_at': 1000, 'message': 'no props at all'},
                'b': {'id': 'b', 'create_at': 1000, 'message': 'none part', 'props': {'ai_part': None}},
                'c': {'id': 'c', 'create_at': 1000, 'message': 'non-int part', 'props': {'ai_part': 'oops'}},
            },
        }
        posts = ai_analyst.normalise_thread(payload)  # must not raise
        self.assertEqual(len(posts), 3)

    def test_create_at_still_wins_when_it_actually_differs(self):
        # ai_part only breaks a TIE; a genuinely later post must still sort
        # after an earlier one regardless of its ai_part.
        payload = {
            'posts': {
                'later': {'id': 'later', 'create_at': 2000, 'message': 'later', 'props': {'ai_part': 0}},
                'earlier': {'id': 'earlier', 'create_at': 1000, 'message': 'earlier', 'props': {'ai_part': 9}},
            },
        }
        posts = ai_analyst.normalise_thread(payload)
        self.assertEqual([p['id'] for p in posts], ['earlier', 'later'])


class AffirmativeTests(unittest.TestCase):
    def test_affirmatives(self):
        for text in ('yes', 'Yes please', '@ai yes', 'yep', 'sure', 'go ahead', 'do it', 'ok'):
            self.assertTrue(ai_analyst.is_affirmative(text, '@ai'), text)

    def test_non_affirmatives(self):
        for text in ('no', 'nope', 'not that one', 'what about the domain?', ''):
            self.assertFalse(ai_analyst.is_affirmative(text, '@ai'), text)

    def test_hedged_and_negated_replies_are_not_approvals(self):
        # These START with an affirmative word but are not approvals. A naive
        # first-word match would green-light a pivot the analyst did not want.
        for text in (
            'ok but why would that domain matter?',
            'yes, but not the IP',
            'sure, except the hash',
            "yeah I don't think so",
        ):
            self.assertFalse(ai_analyst.is_affirmative(text, '@ai'), text)

    # -- Bug (review finding #2): a redirect must not read as approval
    # (#task-4 review) --

    def test_full_approval_matrix_stays_true(self):
        # 'go ahead and pull the C2 infra' is a prefix match on the
        # unambiguous phrase 'go ahead' -- that prefix matching must survive.
        for text in (
            'yes', 'yes please', 'yep', 'sure', 'ok',
            'go ahead', 'go ahead and pull the C2 infra',
            'do it', 'please do', 'proceed', '@ai yes', '@ai full yes',
        ):
            self.assertTrue(ai_analyst.is_affirmative(text, '@ai'), text)

    def test_full_rejection_matrix_stays_false(self):
        for text in (
            'no', 'nope', 'not that one',
            'ok but why would that domain matter?',
            'yes, but not the IP', 'sure, except the hash',
            "yeah I don't think so",
            'what about the domain?', '',
        ):
            self.assertFalse(ai_analyst.is_affirmative(text, '@ai'), text)

    def test_redirect_sentence_fragment_is_not_an_approval(self):
        # 'pull it' / 'check it' are sentence fragments the analyst uses to
        # REDIRECT the bot's proposal, not to approve it. Reading them as a
        # prefix-matched approval silently promotes `pending` to
        # `authorized` and runs a lookup nobody asked for -- the costly
        # direction, since a false negative only costs one round-trip.
        self.assertFalse(ai_analyst.is_affirmative('pull it up in VT instead', '@ai'))


class EvidenceModeParseTests(unittest.TestCase):
    def test_mode_toggle_is_read_after_the_bind(self):
        self.assertEqual(ai_analyst.evidence_mode('@ai full what about 8.8.8.8', '@ai'), 'full')
        self.assertEqual(ai_analyst.evidence_mode('@ai brief thoughts?', '@ai'), 'brief')

    def test_no_toggle_returns_none(self):
        self.assertIsNone(ai_analyst.evidence_mode('@ai what about 8.8.8.8', '@ai'))
        # "full" only counts immediately after the bind, not anywhere in prose.
        self.assertIsNone(ai_analyst.evidence_mode('@ai give me the full picture', '@ai'))


class ReconstructTests(unittest.TestCase):
    def test_user_indicators_become_authorized(self):
        state = _reconstruct([_user('@ai look at 8.8.8.8 and evil.example.com')])
        self.assertEqual(state.authorized, {'8.8.8.8': 'ip', 'evil.example.com': 'domain'})

    def test_bot_narrative_becomes_an_assistant_turn(self):
        state = _reconstruct([_user('@ai check 8.8.8.8'), _reply('The IP is clean.')])
        self.assertEqual(state.history, [
            {'role': 'user', 'content': '@ai check 8.8.8.8'},
            {'role': 'assistant', 'content': 'The IP is clean.'},
        ])

    def test_a_split_reply_is_rejoined_into_one_turn_and_counted_once(self):
        # send_message splits long replies. Without rejoining, the model sees N
        # assistant turns and the thread budget is charged N times.
        state = _reconstruct([
            _user('@ai check 8.8.8.8'),
            _reply('The IP is clean.', tool_calls=3, msg_id='m1', part=0),
            _reply('It resolves to evil.example.com — pull it?', tool_calls=3, msg_id='m1', part=1),
        ])
        self.assertEqual(len(state.history), 2)
        self.assertIn('The IP is clean.', state.history[-1]['content'])
        self.assertIn('pull it?', state.history[-1]['content'])
        self.assertEqual(state.tool_calls_used, 3, 'a split reply was double-counted')
        # And the pivot named in the SECOND part must still be pending.
        self.assertEqual(state.pending, {'evil.example.com': 'domain'})

    def test_evidence_posts_are_never_replayed_to_the_model(self):
        state = _reconstruct([
            _user('@ai full check 8.8.8.8'),
            _reply('The IP is clean.'),
            _evidence('| header | table |\n|---|---|\n| a huge | raw dump |'),
        ])
        self.assertEqual(len(state.history), 2)
        self.assertNotIn('raw dump', json.dumps(state.history))

    def test_indicators_the_bot_names_are_pending_not_authorized(self):
        state = _reconstruct([
            _user('@ai check 8.8.8.8'),
            _reply('That IP is clean. It resolves to evil.example.com — want me to pull it?'),
        ])
        self.assertIn('8.8.8.8', state.authorized)
        self.assertNotIn('evil.example.com', state.authorized)
        self.assertEqual(state.pending, {'evil.example.com': 'domain'})

    def test_affirmative_reply_promotes_pending_to_authorized(self):
        state = _reconstruct([
            _user('@ai check 8.8.8.8'),
            _reply('It resolves to evil.example.com — want me to pull it?'),
            _user('yes'),
        ])
        self.assertIn('evil.example.com', state.authorized)
        self.assertEqual(state.pending, {})

    def test_hedged_reply_does_not_promote_pending(self):
        state = _reconstruct([
            _user('@ai check 8.8.8.8'),
            _reply('It resolves to evil.example.com — want me to pull it?'),
            _user('ok but why would that domain matter?'),
        ])
        self.assertNotIn('evil.example.com', state.authorized)

    def test_naming_an_indicator_authorizes_only_that_one(self):
        state = _reconstruct([
            _user('@ai check 8.8.8.8'),
            _reply('I see evil.example.com and bad.example.org — pull them?'),
            _user('@ai just evil.example.com please'),
        ])
        self.assertIn('evil.example.com', state.authorized)
        self.assertNotIn('bad.example.org', state.authorized)

    def test_evidence_mode_is_sticky_and_last_write_wins(self):
        self.assertEqual(_reconstruct([_user('@ai check 8.8.8.8')]).mode, 'compact')
        state = _reconstruct([
            _user('@ai full check 8.8.8.8'), _reply('clean'), _user('@ai and 1.1.1.1?'),
        ])
        self.assertEqual(state.mode, 'full')
        state = _reconstruct([
            _user('@ai full check 8.8.8.8'), _reply('clean'), _user('@ai brief and 1.1.1.1?'),
        ])
        self.assertEqual(state.mode, 'compact')

    def test_thread_tool_budget_is_summed_from_post_props(self):
        state = _reconstruct([
            _user('@ai check 8.8.8.8'), _reply('clean', tool_calls=3, msg_id='m1'),
            _user('@ai and 1.1.1.1?'), _reply('also clean', tool_calls=2, msg_id='m2'),
        ])
        self.assertEqual(state.tool_calls_used, 5)

    def test_history_is_capped_to_the_most_recent_turns(self):
        posts = []
        for i in range(30):
            posts.append(_user(f'@ai message {i}'))
            posts.append(_reply(f'reply {i}', msg_id=f'm{i}'))
        state = _reconstruct(posts, max_history_turns=4)
        self.assertEqual(len(state.history), 4)
        self.assertEqual(state.history[-1]['content'], 'reply 29')

    def test_authorization_survives_the_history_cap(self):
        # Trimming the model's context must not silently de-authorize an indicator
        # the analyst named 30 turns ago.
        posts = [_user('@ai check 8.8.8.8')]
        for i in range(30):
            posts.append(_reply(f'reply {i}', msg_id=f'm{i}'))
            posts.append(_user(f'@ai message {i}'))
        state = _reconstruct(posts, max_history_turns=4)
        self.assertIn('8.8.8.8', state.authorized)

    def test_foreign_bot_posts_are_ignored(self):
        # @ioc output from an ordinary command can live in the same thread.
        posts = [_user('@ai check 8.8.8.8'), {'user_id': BOT, 'message': '| ioc |', 'props': {}}]
        self.assertEqual(len(_reconstruct(posts).history), 1)

    # -- Bug (review finding #1): a split reply must rejoin in SEND order even
    # when create_at ties and post ids sort the other way (#task-4 review) --

    def test_split_reply_rejoins_in_send_order_despite_tied_create_at_and_backwards_ids(self):
        # Reproduces the reviewer's exact scenario: part 1 (the pivot
        # proposal) has an id that sorts BEFORE part 0's id (the sentence
        # that leads up to it), and both parts share one create_at because
        # send_message() posts them back-to-back in a tight loop. Only
        # ai_part encodes true send order.
        payload = {
            'posts': {
                'b7m3n': {
                    'id': 'b7m3n', 'user_id': BOT, 'create_at': 1000,
                    'message': 'It resolves to evil.example.com — pull it?',
                    'props': {
                        ai_analyst.PROP_KEY: ai_analyst.PROP_REPLY,
                        ai_analyst.PROP_TOOL_CALLS: 3,
                        ai_analyst.PROP_MSG_ID: 'm1',
                        ai_analyst.PROP_PART: 1,
                    },
                },
                'xk2np': {
                    'id': 'xk2np', 'user_id': BOT, 'create_at': 1000,
                    'message': 'The IP is clean.',
                    'props': {
                        ai_analyst.PROP_KEY: ai_analyst.PROP_REPLY,
                        ai_analyst.PROP_TOOL_CALLS: 3,
                        ai_analyst.PROP_MSG_ID: 'm1',
                        ai_analyst.PROP_PART: 0,
                    },
                },
                'root': {
                    'id': 'root', 'user_id': HUMAN, 'create_at': 500,
                    'message': '@ai check 8.8.8.8', 'props': {},
                },
            },
        }
        posts = ai_analyst.normalise_thread(payload)
        state = ai_analyst.reconstruct(posts, BOT, 'compact', 20, '@ai')
        content = state.history[-1]['content']
        self.assertLess(
            content.index('The IP is clean.'), content.index('pull it?'),
            'parts rejoined out of send order: %r' % content,
        )
        # The split reply's tool budget must still be charged exactly once.
        self.assertEqual(state.tool_calls_used, 3)

    def test_three_part_split_reply_rejoins_in_send_order_with_shuffled_ids(self):
        payload = {
            'posts': {
                'm-id-c': {
                    'id': 'm-id-c', 'user_id': BOT, 'create_at': 2000,
                    'message': 'third part',
                    'props': {
                        ai_analyst.PROP_KEY: ai_analyst.PROP_REPLY,
                        ai_analyst.PROP_TOOL_CALLS: 1,
                        ai_analyst.PROP_MSG_ID: 'm2',
                        ai_analyst.PROP_PART: 2,
                    },
                },
                'a-id-first': {
                    'id': 'a-id-first', 'user_id': BOT, 'create_at': 2000,
                    'message': 'first part',
                    'props': {
                        ai_analyst.PROP_KEY: ai_analyst.PROP_REPLY,
                        ai_analyst.PROP_TOOL_CALLS: 1,
                        ai_analyst.PROP_MSG_ID: 'm2',
                        ai_analyst.PROP_PART: 0,
                    },
                },
                'z-id-mid': {
                    'id': 'z-id-mid', 'user_id': BOT, 'create_at': 2000,
                    'message': 'second part',
                    'props': {
                        ai_analyst.PROP_KEY: ai_analyst.PROP_REPLY,
                        ai_analyst.PROP_TOOL_CALLS: 1,
                        ai_analyst.PROP_MSG_ID: 'm2',
                        ai_analyst.PROP_PART: 1,
                    },
                },
            },
        }
        posts = ai_analyst.normalise_thread(payload)
        state = ai_analyst.reconstruct(posts, BOT, 'compact', 20, '@ai')
        content = state.history[-1]['content']
        self.assertLess(content.index('first part'), content.index('second part'))
        self.assertLess(content.index('second part'), content.index('third part'))
        self.assertEqual(state.tool_calls_used, 1)


class FakeResponse(object):
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession(object):
    """Stands in for requests.Session so the client is testable with no network."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({'url': url, 'headers': headers, 'json': json, 'timeout': timeout})
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


class LLMClientTests(unittest.TestCase):
    def _client(self, *responses, **kwargs):
        session = FakeSession(*responses)
        client = ai_analyst.LLMClient(
            base_url='http://localhost:11434/v1', api_key='ollama',
            model='some-model', timeout=60, session=session, **kwargs)
        return client, session

    def test_posts_to_chat_completions_with_tools(self):
        client, session = self._client(
            FakeResponse({'choices': [{'message': {'role': 'assistant', 'content': 'hi'}}]}))
        client.chat([{'role': 'user', 'content': 'hi'}], [{'type': 'function'}])
        call = session.calls[0]
        self.assertEqual(call['url'], 'http://localhost:11434/v1/chat/completions')
        self.assertEqual(call['headers']['Authorization'], 'Bearer ollama')
        self.assertEqual(call['json']['model'], 'some-model')
        self.assertEqual(call['json']['tools'], [{'type': 'function'}])
        self.assertEqual(call['json']['temperature'], 0)
        self.assertEqual(call['timeout'], 60)

    def test_omits_the_tools_key_when_there_are_no_tools(self):
        # Some endpoints reject an empty tools array outright.
        client, session = self._client(
            FakeResponse({'choices': [{'message': {'role': 'assistant', 'content': 'hi'}}]}))
        client.chat([{'role': 'user', 'content': 'hi'}], [])
        self.assertNotIn('tools', session.calls[0]['json'])

    def test_normalises_a_text_answer(self):
        client, _ = self._client(FakeResponse(
            {'choices': [{'message': {'role': 'assistant', 'content': 'The IP is clean.'}}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['content'], 'The IP is clean.')
        self.assertEqual(reply['tool_calls'], [])

    def test_normalises_tool_calls_and_parses_json_arguments(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant', 'content': None,
            'tool_calls': [{'id': 'call_1', 'type': 'function', 'function': {
                'name': 'crtsh', 'arguments': '{"query": "evil.example.com"}'}}],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['content'], '')
        self.assertEqual(reply['tool_calls'], [
            {'id': 'call_1', 'name': 'crtsh', 'arguments': {'query': 'evil.example.com'}}])
        # The provider's own message must be echoed back verbatim next request.
        self.assertEqual(reply['raw_message']['tool_calls'][0]['id'], 'call_1')

    def test_malformed_tool_arguments_do_not_raise(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'call_1', 'function': {
                'name': 'crtsh', 'arguments': 'not json at all'}}],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'][0]['arguments'], {})

    def test_retries_once_on_a_transient_error_then_succeeds(self):
        ok = {'choices': [{'message': {'role': 'assistant', 'content': 'recovered'}}]}
        client, session = self._client(FakeResponse({}, 503), FakeResponse(ok))
        reply = client.chat([], [])
        self.assertEqual(reply['content'], 'recovered')
        self.assertEqual(len(session.calls), 2)

    def test_http_error_raises_llmerror_without_leaking_the_key(self):
        client, _ = self._client(FakeResponse({'error': 'nope'}, 401))
        with self.assertRaises(ai_analyst.LLMError) as ctx:
            client.chat([], [])
        self.assertNotIn('ollama', str(ctx.exception))

    def test_no_choices_still_raises_a_clean_llmerror(self):
        client, _ = self._client(FakeResponse({}))
        with self.assertRaises(ai_analyst.LLMError):
            client.chat([], [])

    def test_empty_choices_list_still_raises_a_clean_llmerror(self):
        client, _ = self._client(FakeResponse({'choices': []}))
        with self.assertRaises(ai_analyst.LLMError):
            client.chat([], [])

    def test_null_content_with_no_tool_calls_normalises_to_empty(self):
        client, _ = self._client(FakeResponse(
            {'choices': [{'message': {'role': 'assistant', 'content': None}}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['content'], '')
        self.assertEqual(reply['tool_calls'], [])

    def test_arguments_as_dict_pass_through(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'call_1', 'function': {
                'name': 'crtsh', 'arguments': {'query': 'evil.example.com'}}}],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'][0]['arguments'], {'query': 'evil.example.com'})

    def test_empty_string_arguments_normalise_to_empty_dict(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'call_1', 'function': {'name': 'crtsh', 'arguments': ''}}],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'][0]['arguments'], {})

    def test_none_arguments_normalise_to_empty_dict(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'call_1', 'function': {'name': 'crtsh', 'arguments': None}}],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'][0]['arguments'], {})

    def test_tool_call_missing_id_and_name_still_normalises(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant',
            'tool_calls': [{'function': {'arguments': '{}'}}],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'], [{'id': None, 'name': None, 'arguments': {}}])

    def test_message_not_a_dict_raises_llmerror_not_attributeerror(self):
        # Local model servers (Ollama/vLLM) can emit a degenerate structure where
        # `message` itself is a bare string instead of an object.
        client, _ = self._client(FakeResponse({'choices': [{'message': 'oops-not-a-dict'}]}))
        with self.assertRaises(ai_analyst.LLMError):
            client.chat([], [])

    def test_tool_calls_not_a_list_is_treated_as_no_tool_calls(self):
        # Quantized local models sometimes emit `tool_calls` as an object instead
        # of an array when JSON generation degrades.
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant', 'content': 'hi',
            'tool_calls': {'weird': 'dict'},
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'], [])
        self.assertEqual(reply['content'], 'hi')

    def test_tool_calls_list_of_non_dicts_is_skipped(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant', 'content': None,
            'tool_calls': ['not-a-dict'],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'], [])

    def test_tool_call_function_not_a_dict_is_skipped(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant', 'content': None,
            'tool_calls': [{'id': 'call_1', 'function': 'oops'}],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'], [])

    def test_mixed_list_keeps_the_valid_call_and_skips_the_malformed_one(self):
        client, _ = self._client(FakeResponse({'choices': [{'message': {
            'role': 'assistant', 'content': None,
            'tool_calls': [
                {'id': 'call_1', 'function': {'name': 'crtsh', 'arguments': '{}'}},
                'not-a-dict',
            ],
        }}]}))
        reply = client.chat([], [])
        self.assertEqual(reply['tool_calls'], [
            {'id': 'call_1', 'name': 'crtsh', 'arguments': {}}])

    def test_raw_message_is_echoed_back_verbatim_even_when_malformed(self):
        raw = {'role': 'assistant', 'content': None, 'tool_calls': ['not-a-dict']}
        client, _ = self._client(FakeResponse({'choices': [{'message': raw}]}))
        reply = client.chat([], [])
        self.assertIs(reply['raw_message'], raw)


class StubExecutor(object):
    """Records what actually reached module execution. Nothing else may."""

    def __init__(self, output='module output'):
        self.output = output
        self.calls = []

    async def __call__(self, module, command, channame, username, params):
        self.calls.append({'module': module, 'command': command, 'channame': channame,
                           'username': username, 'params': params})
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class StubPoster(object):
    def __init__(self):
        self.posts = []

    async def __call__(self, chanid, text, rootid, props=None):
        self.posts.append({'chanid': chanid, 'text': text, 'rootid': rootid, 'props': props})


class FakeLLM(object):
    """Replays a scripted list of replies, in order, and records what it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def chat(self, messages, tools):
        self.requests.append({'messages': list(messages), 'tools': list(tools)})
        if not self.replies:
            return {'content': 'done', 'tool_calls': [], 'raw_message': {'role': 'assistant'}}
        return self.replies.pop(0)


def _answer(text):
    return {'content': text, 'tool_calls': [],
            'raw_message': {'role': 'assistant', 'content': text}}


def _tool_call(name, query, call_id='call_1'):
    return {
        'content': '',
        'tool_calls': [{'id': call_id, 'name': name, 'arguments': {'query': query}}],
        'raw_message': {'role': 'assistant', 'tool_calls': [{'id': call_id}]},
    }


DEFAULT_CONFIG = {
    'bind': '@ai', 'evidence': 'compact', 'max_tool_calls_per_turn': 8,
    'max_tool_calls_per_thread': 40, 'max_iterations': 6, 'max_history_turns': 20,
    'max_evidence_chars': 4000, 'modules': [], 'blocked_modules': [],
}


def _analyst(llm, thread=None, executor=None, poster=None, allowed=True, config=None,
             registry=None):
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(config or {})
    thread = thread or []

    async def get_thread(rootid, exclude_post_id=None):
        return [p for p in thread if p.get('id') != exclude_post_id]

    return ai_analyst.AIAnalyst(
        config=cfg,
        get_registry=(lambda: registry if registry is not None else _registry()),
        run_tool=executor or StubExecutor(),
        get_thread=get_thread,
        post=poster or StubPoster(),
        is_allowed=(lambda userid, module, chaninfo: allowed),
        llm=llm,
        bot_id=BOT,
    )


async def _handle(analyst, message, post_id='p-now', rootid='root-1'):
    await analyst.handle(
        userid=HUMAN, username='alice', chanid='chan-1', channame='soc',
        chaninfo={'name': 'soc'}, rootid=rootid, post_id=post_id, message=message)


class AuthorizationGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_an_indicator_the_analyst_named_runs(self):
        executor = StubExecutor()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Certificates found.')])
        await _handle(_analyst(llm, executor=executor), '@ai what about evil.example.com?')
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(executor.calls[0]['module'], 'crtsh')
        self.assertEqual(executor.calls[0]['params'], ['evil.example.com'])
        # Executed via the module's first BIND, as an @-command would be.
        self.assertEqual(executor.calls[0]['command'], '@crtsh')

    async def test_an_unauthorized_indicator_is_refused_at_the_executor(self):
        # The model tries to pivot to an indicator the analyst never named. This
        # must be impossible in code, not merely discouraged in the prompt.
        executor = StubExecutor()
        llm = FakeLLM([
            _tool_call('crtsh', 'attacker-pivot.example.com'),
            _answer('It resolves to attacker-pivot.example.com — want me to pull it?'),
        ])
        await _handle(_analyst(llm, executor=executor), '@ai what about evil.example.com?')
        self.assertEqual(executor.calls, [], 'an unauthorized lookup reached a module')
        tool_result = llm.requests[-1]['messages'][-1]
        self.assertEqual(tool_result['role'], 'tool')
        self.assertIn('not been approved', tool_result['content'])

    async def test_an_approved_pivot_runs_on_the_next_turn(self):
        executor = StubExecutor()
        thread = [
            {'id': 'p1', **_user('@ai what about evil.example.com?')},
            {'id': 'p2', **_reply('It resolves to 9.9.9.9 — want me to pull it?')},
        ]
        llm = FakeLLM([_tool_call('circlpdns', '9.9.9.9'), _answer('A known sinkhole.')])
        await _handle(_analyst(llm, thread=thread, executor=executor), 'yes', post_id='p3')
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(executor.calls[0]['params'], ['9.9.9.9'])

    async def test_a_declined_pivot_stays_blocked(self):
        executor = StubExecutor()
        thread = [
            {'id': 'p1', **_user('@ai what about evil.example.com?')},
            {'id': 'p2', **_reply('It resolves to 9.9.9.9 — want me to pull it?')},
        ]
        llm = FakeLLM([_tool_call('circlpdns', '9.9.9.9'), _answer('Understood.')])
        await _handle(_analyst(llm, thread=thread, executor=executor), 'no, leave it', post_id='p3')
        self.assertEqual(executor.calls, [])


class OperatorAllowListTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_blocked_module_is_neither_offered_nor_runnable(self):
        executor = StubExecutor()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Cannot use crtsh.')])
        analyst = _analyst(llm, executor=executor, config={'blocked_modules': ['crtsh']})
        await _handle(analyst, '@ai check evil.example.com')
        self.assertNotIn('crtsh', {t['function']['name'] for t in llm.requests[0]['tools']})
        self.assertEqual(executor.calls, [], 'a blocked module was executed')

    async def test_an_allow_list_excludes_everything_else(self):
        executor = StubExecutor()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Nope.')])
        analyst = _analyst(llm, executor=executor, config={'modules': ['circlpdns']})
        await _handle(analyst, '@ai check evil.example.com')
        self.assertEqual({t['function']['name'] for t in llm.requests[0]['tools']}, {'circlpdns'})
        self.assertEqual(executor.calls, [])


class TypeAndAclGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_module_is_not_called_with_a_type_it_does_not_accept(self):
        executor = StubExecutor()
        # crtsh is domain-only; the model tries to hand it a hash.
        llm = FakeLLM([_tool_call('crtsh', 'd41d8cd98f00b204e9800998ecf8427e'),
                       _answer('crtsh cannot take a hash.')])
        await _handle(_analyst(llm, executor=executor),
                      '@ai look at d41d8cd98f00b204e9800998ecf8427e')
        self.assertEqual(executor.calls, [])
        self.assertIn('does not accept', llm.requests[-1]['messages'][-1]['content'])

    async def test_acl_denial_blocks_the_call(self):
        executor = StubExecutor()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Could not query.')])
        await _handle(_analyst(llm, executor=executor, allowed=False),
                      '@ai check evil.example.com')
        self.assertEqual(executor.calls, [])
        self.assertIn('not permitted', llm.requests[-1]['messages'][-1]['content'])

    async def test_a_non_aitool_module_cannot_be_called(self):
        executor = StubExecutor()
        llm = FakeLLM([_tool_call('diceroll', 'evil.example.com'), _answer('No such tool.')])
        await _handle(_analyst(llm, executor=executor), '@ai check evil.example.com')
        self.assertEqual(executor.calls, [])

    async def test_an_unclassifiable_query_is_rejected(self):
        executor = StubExecutor()
        llm = FakeLLM([_tool_call('crtsh', 'not-an-indicator'), _answer('Not an indicator.')])
        await _handle(_analyst(llm, executor=executor), '@ai check evil.example.com')
        self.assertEqual(executor.calls, [])


class ToolOutputSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_module_exception_never_reaches_the_model_or_the_channel(self):
        # An exception string can carry a key-bearing URL (#285). It must not be
        # posted, and it must not be fed back to the model either.
        executor = StubExecutor(output=RuntimeError('https://api.example.test/?key=SECRET123'))
        poster = StubPoster()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('The lookup failed.')])
        await _handle(_analyst(llm, executor=executor, poster=poster),
                      '@ai check evil.example.com')
        tool_result = llm.requests[-1]['messages'][-1]['content']
        self.assertNotIn('SECRET123', tool_result)
        self.assertIn('failed', tool_result.lower())
        self.assertNotIn('SECRET123', json.dumps(poster.posts))

    async def test_credentials_in_SUCCESSFUL_module_output_are_redacted(self):
        # #286 only fixed exception text. A module's success output can cite a
        # key-bearing source URL -- and the AI ships that text OFF-HOST to an LLM.
        executor = StubExecutor(
            output='Source: https://api.example.test/v2/8.8.8.8?key=NOTAREALKEY0002')
        poster = StubPoster()
        llm = FakeLLM([_tool_call('circlpdns', '8.8.8.8'), _answer('Sinkholed.')])
        await _handle(_analyst(llm, executor=executor, poster=poster,
                               config={'evidence': 'full'}), '@ai check 8.8.8.8')
        self.assertNotIn('NOTAREALKEY0002', json.dumps(llm.requests))
        self.assertNotIn('NOTAREALKEY0002', json.dumps(poster.posts))

    async def test_oversized_module_output_is_capped(self):
        executor = StubExecutor(output='A' * 10000)
        llm = FakeLLM([_tool_call('circlpdns', '8.8.8.8'), _answer('Lots of data.')])
        analyst = _analyst(llm, executor=executor, config={'max_evidence_chars': 500})
        await _handle(analyst, '@ai check 8.8.8.8')
        tool_result = llm.requests[-1]['messages'][-1]['content']
        self.assertLess(len(tool_result), 1000)
        self.assertIn('truncated', tool_result.lower())


class AgentLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_plain_answer_is_posted_as_the_narrative(self):
        poster = StubPoster()
        llm = FakeLLM([_answer('The hash is Emotet; the IP is clean. Looks like staging.')])
        await _handle(_analyst(llm, poster=poster), '@ai thoughts?')
        self.assertEqual(len(poster.posts), 1)
        self.assertIn('Emotet', poster.posts[0]['text'])
        self.assertEqual(poster.posts[0]['props'][ai_analyst.PROP_KEY], ai_analyst.PROP_REPLY)
        self.assertTrue(poster.posts[0]['props'][ai_analyst.PROP_MSG_ID])

    async def test_a_conceptual_turn_exposes_no_tools_at_all(self):
        llm = FakeLLM([_answer('Beaconing usually means a scheduled callback.')])
        await _handle(_analyst(llm), '@ai what does beaconing usually indicate?')
        self.assertEqual(llm.requests[0]['tools'], [])

    async def test_the_system_prompt_leads_and_history_is_replayed(self):
        thread = [
            {'id': 'p1', **_user('@ai check evil.example.com')},
            {'id': 'p2', **_reply('Nothing on it.')},
        ]
        llm = FakeLLM([_answer('Still nothing.')])
        await _handle(_analyst(llm, thread=thread), '@ai anything new?', post_id='p3')
        roles = [m['role'] for m in llm.requests[0]['messages']]
        self.assertEqual(roles[0], 'system')
        self.assertEqual(roles[-1], 'user')
        self.assertIn('assistant', roles)
        self.assertEqual(llm.requests[0]['messages'][-1]['content'], '@ai anything new?')

    async def test_the_model_is_told_what_is_approved_and_what_is_pending(self):
        # Exposure is type-narrowed and the executor is the real gate, but telling
        # the model the authorization state stops it wasting calls on blocked pivots.
        thread = [
            {'id': 'p1', **_user('@ai check evil.example.com')},
            {'id': 'p2', **_reply('It resolves to 9.9.9.9 — want me to pull it?')},
        ]
        llm = FakeLLM([_answer('Waiting on you.')])
        await _handle(_analyst(llm, thread=thread), '@ai hold on', post_id='p3')
        context = '\n'.join(m['content'] for m in llm.requests[0]['messages']
                            if m['role'] == 'system')
        self.assertIn('evil.example.com', context)
        self.assertIn('9.9.9.9', context)
        self.assertIn('pending', context.lower())

    async def test_the_current_post_is_not_double_counted_from_the_thread(self):
        # The webhook fires after the post exists, so get_thread() may contain it.
        thread = [{'id': 'p-now', **_user('@ai check evil.example.com')}]
        llm = FakeLLM([_answer('Checked.')])
        await _handle(_analyst(llm, thread=thread), '@ai check evil.example.com',
                      post_id='p-now')
        users = [m for m in llm.requests[0]['messages'] if m['role'] == 'user']
        self.assertEqual(len(users), 1)

    async def test_tool_results_are_fed_back_as_delimited_untrusted_data(self):
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Two certs.')])
        await _handle(_analyst(llm, executor=StubExecutor(output='| cert | issuer |')),
                      '@ai check evil.example.com')
        last = llm.requests[1]['messages'][-1]
        self.assertEqual(last['role'], 'tool')
        self.assertEqual(last['tool_call_id'], 'call_1')
        self.assertIn('untrusted_tool_result', last['content'])
        self.assertIn('| cert | issuer |', last['content'])

    async def test_the_iteration_cap_ends_the_loop(self):
        # A model that only ever asks for tools must not loop forever.
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com', call_id=f'c{i}')
                       for i in range(10)])
        poster = StubPoster()
        await _handle(_analyst(llm, poster=poster, config={'max_iterations': 3}),
                      '@ai check evil.example.com')
        self.assertEqual(len(llm.requests), 3)
        self.assertIn('could not finish', poster.posts[-1]['text'].lower())

    async def test_the_per_turn_tool_cap_is_enforced(self):
        executor = StubExecutor()
        calls = [
            {'content': '', 'raw_message': {'role': 'assistant'}, 'tool_calls': [
                {'id': 'a', 'name': 'crtsh', 'arguments': {'query': 'evil.example.com'}},
                {'id': 'b', 'name': 'crtsh', 'arguments': {'query': 'evil.example.com'}},
                {'id': 'c', 'name': 'crtsh', 'arguments': {'query': 'evil.example.com'}},
            ]},
            _answer('Enough.'),
        ]
        await _handle(_analyst(FakeLLM(calls), executor=executor,
                               config={'max_tool_calls_per_turn': 2}),
                      '@ai check evil.example.com')
        self.assertEqual(len(executor.calls), 2)

    async def test_the_per_thread_tool_cap_counts_earlier_turns(self):
        executor = StubExecutor()
        thread = [
            {'id': 'p1', **_user('@ai check evil.example.com')},
            {'id': 'p2', **_reply('Nothing.', tool_calls=5)},
        ]
        await _handle(_analyst(FakeLLM([_tool_call('crtsh', 'evil.example.com'),
                                        _answer('Done.')]),
                               thread=thread, executor=executor,
                               config={'max_tool_calls_per_thread': 5}),
                      '@ai check evil.example.com again', post_id='p3')
        self.assertEqual(executor.calls, [], 'thread budget was already spent')

    async def test_the_reply_records_the_tools_it_spent(self):
        poster = StubPoster()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Two certs.')])
        await _handle(_analyst(llm, poster=poster), '@ai check evil.example.com')
        self.assertEqual(poster.posts[-1]['props'][ai_analyst.PROP_TOOL_CALLS], 1)

    async def test_a_timed_out_lookup_is_not_reported_as_ok(self):
        poster = StubPoster()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('crt.sh was slow.')])
        await _handle(_analyst(llm, poster=poster,
                               executor=StubExecutor(output='The crtsh lookup timed out.')),
                      '@ai check evil.example.com')
        self.assertIn('crtsh(evil.example.com) → timed out', poster.posts[0]['text'])


class EvidenceModeLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_compact_posts_a_narrative_and_a_sources_footer_only(self):
        poster = StubPoster()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Two certs.')])
        await _handle(_analyst(llm, poster=poster,
                               executor=StubExecutor(output='| RAW TABLE |')),
                      '@ai check evil.example.com')
        self.assertEqual(len(poster.posts), 1)
        text = poster.posts[0]['text']
        self.assertIn('Two certs.', text)
        self.assertIn('crtsh(evil.example.com)', text)
        self.assertNotIn('RAW TABLE', text)

    async def test_full_posts_the_narrative_then_tagged_evidence(self):
        poster = StubPoster()
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Two certs.')])
        await _handle(_analyst(llm, poster=poster,
                               executor=StubExecutor(output='| RAW TABLE |'),
                               config={'evidence': 'full'}),
                      '@ai check evil.example.com')
        self.assertEqual(len(poster.posts), 2)
        self.assertIn('Two certs.', poster.posts[0]['text'])
        self.assertEqual(poster.posts[0]['props'][ai_analyst.PROP_KEY], ai_analyst.PROP_REPLY)
        self.assertIn('RAW TABLE', poster.posts[1]['text'])
        self.assertEqual(poster.posts[1]['props'][ai_analyst.PROP_KEY], ai_analyst.PROP_EVIDENCE)

    async def test_full_is_sticky_for_the_thread(self):
        poster = StubPoster()
        thread = [
            {'id': 'p1', **_user('@ai full check evil.example.com')},
            {'id': 'p2', **_reply('Two certs.')},
        ]
        llm = FakeLLM([_tool_call('crtsh', 'evil.example.com'), _answer('Still two.')])
        await _handle(_analyst(llm, thread=thread, poster=poster,
                               executor=StubExecutor(output='| RAW TABLE |')),
                      '@ai anything new?', post_id='p3')
        self.assertEqual(poster.posts[1]['props'][ai_analyst.PROP_KEY], ai_analyst.PROP_EVIDENCE)


class LLMFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_an_llm_failure_posts_a_clean_message(self):
        class BrokenLLM(object):
            def chat(self, messages, tools):
                raise ai_analyst.LLMError('LLM endpoint returned HTTP 500')

        poster = StubPoster()
        await _handle(_analyst(BrokenLLM(), poster=poster), '@ai check evil.example.com')
        self.assertEqual(len(poster.posts), 1)
        self.assertIn('could not reach', poster.posts[0]['text'].lower())

    async def test_a_thread_fetch_failure_posts_a_clean_message(self):
        async def broken_thread(rootid, exclude_post_id=None):
            raise RuntimeError('mattermost is down')

        poster = StubPoster()
        analyst = _analyst(FakeLLM([_answer('unused')]), poster=poster)
        analyst.get_thread = broken_thread
        await _handle(analyst, '@ai check evil.example.com')
        self.assertIn('could not read this thread', poster.posts[0]['text'].lower())


class AdversarialExecutorTests(unittest.IsolatedAsyncioTestCase):
    """Drive _run_tool_call directly with hostile/malformed shapes.

    The point of the executor is that a prompt-injected or malfunctioning model
    cannot reach a module with an indicator the analyst never authorized -- no
    matter what shape `name`/`arguments` take. These tests execute the gate,
    they do not just read it.
    """

    def _ctx(self):
        return {'userid': HUMAN, 'username': 'alice', 'channame': 'soc', 'chaninfo': {'name': 'soc'}}

    async def test_query_none_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': None}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_query_int_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': 12345}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_query_dict_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': {'evil.example.com': 'domain'}}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_query_list_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': ['evil.example.com']}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_arguments_not_a_dict_list_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'crtsh', ['evil.example.com'], state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_arguments_a_string_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        result, did_run = await analyst._run_tool_call(
            'crtsh', 'evil.example.com', state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_arguments_none_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        result, did_run = await analyst._run_tool_call(
            'crtsh', None, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_name_none_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        result, did_run = await analyst._run_tool_call(
            None, {'query': 'evil.example.com'}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_name_a_list_is_denied_not_crashed(self):
        # An unhashable name (list/dict) must not raise out of a dict.get().
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        result, did_run = await analyst._run_tool_call(
            ['crtsh'], {'query': 'evil.example.com'}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_name_a_dict_is_denied_not_crashed(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        result, did_run = await analyst._run_tool_call(
            {'name': 'crtsh'}, {'query': 'evil.example.com'}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_name_not_in_registry_is_denied(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'nonexistent_module', {'query': 'evil.example.com'}, state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_case_variant_of_an_authorized_domain_still_matches(self):
        # cmdutils.classify() lowercases domains -- the same normalisation that
        # built state.authorized in the first place -- so a case variant of an
        # already-authorized indicator is recognised, not silently rejected.
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': 'EVIL.EXAMPLE.COM'}, state, self._ctx(), 0)
        self.assertTrue(did_run)
        self.assertEqual(executor.calls[0]['params'], ['evil.example.com'])

    async def test_whitespace_padded_authorized_domain_still_matches(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': '  evil.example.com  '}, state, self._ctx(), 0)
        self.assertTrue(did_run)
        self.assertEqual(executor.calls[0]['params'], ['evil.example.com'])

    async def test_defanged_variant_of_an_authorized_domain_still_matches(self):
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': 'evil[.]example[.]com'}, state, self._ctx(), 0)
        self.assertTrue(did_run)
        self.assertEqual(executor.calls[0]['params'], ['evil.example.com'])

    async def test_query_smuggling_an_authorized_plus_unauthorized_value_is_denied(self):
        # A model that tries to piggyback an unauthorized pivot onto an
        # authorized one in a single query string must not classify as the
        # authorized value alone -- the combined string must fail to classify
        # at all, so nothing runs.
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        state.authorized['evil.example.com'] = 'domain'
        result, did_run = await analyst._run_tool_call(
            'crtsh', {'query': 'evil.example.com; attacker-pivot.example.org'},
            state, self._ctx(), 0)
        self.assertFalse(did_run)
        self.assertEqual(executor.calls, [])

    async def test_refusal_path_consumes_no_budget(self):
        # Denials must return did_run=False so calls_this_turn (accumulated by
        # the caller) never increments for a blocked call -- otherwise a model
        # that keeps proposing unauthorized pivots could starve the budget for
        # lookups the analyst actually asked for.
        executor = StubExecutor()
        analyst = _analyst(FakeLLM([]), executor=executor)
        state = ai_analyst.ThreadState()
        calls_this_turn = 0
        for _ in range(5):
            result, did_run = await analyst._run_tool_call(
                'crtsh', {'query': 'never-authorized.example.com'},
                state, self._ctx(), calls_this_turn)
            if did_run:
                calls_this_turn += 1
        self.assertEqual(calls_this_turn, 0)
        self.assertEqual(executor.calls, [])

    async def test_malformed_tool_call_entry_in_the_loop_does_not_crash_handle(self):
        # A degenerate LLM response can put a non-dict entry in tool_calls (the
        # same shape LLMClient._normalise_tool_calls already has to defend
        # against on the provider-JSON side). handle()'s own loop must survive
        # it too.
        poster = StubPoster()
        calls = [
            {'content': '', 'raw_message': {'role': 'assistant'}, 'tool_calls': [
                'not-a-dict',
                {'id': 'a', 'name': 'crtsh', 'arguments': {'query': 'evil.example.com'}},
            ]},
            _answer('Done.'),
        ]
        executor = StubExecutor()
        await _handle(_analyst(FakeLLM(calls), executor=executor, poster=poster),
                      '@ai check evil.example.com')
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(executor.calls[0]['params'], ['evil.example.com'])


if __name__ == "__main__":
    unittest.main()
