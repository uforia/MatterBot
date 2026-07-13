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


if __name__ == "__main__":
    unittest.main()
