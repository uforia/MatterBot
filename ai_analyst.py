#!/usr/bin/env python3

"""Conversational AI analyst: the command modules, used as tools by an LLM.

An analyst says `@ai we're seeing beacons to 8.8.8[.]8, thoughts?` in a channel.
This module reconstructs the case from the Mattermost thread, decides which
command modules could speak to the indicators in play, lets an LLM call them, and
writes the answer back in the thread. The thread IS the case: there is no
server-side session, so a restart loses nothing.

Three rules shape the design:

1. **The executor is the only door.** Everything the model wants to happen goes
   through AIAnalyst._run_tool_call(), which enforces the operator allow-list,
   ACLs, indicator-type acceptance, analyst authorization and call caps in code.
   Prompting is not a control. Tool results are attacker-influenceable (WHOIS
   registrant text, filenames, urlscan page content, MISP comments), so indirect
   prompt injection is in scope -- and the answer to it is that a hijacked model
   still cannot do anything but a read-only, authorized, ACL-checked, rate-capped
   lookup.

2. **Module output is redacted before it goes anywhere.** This feature is the
   first thing in MatterBot that ships module output OFF-HOST, to a third-party
   LLM endpoint. That is new exfiltration surface, and it exists for success
   output, not just for exception text -- so sanitize_tool_output() runs on every
   byte, whatever the module did. Do not delegate this to the modules.

3. **Import-light.** The CI runner installs no dependencies, so this file must
   import with stdlib + commands/cmdutils.py alone. `requests` is imported lazily
   inside LLMClient, never at module top.
"""

import logging
import re

from commands import cmdutils

log = logging.getLogger('MatterBot')

# Written into the props of every post the analyst makes. Reconstruction reads
# them back to work out what it is looking at:
#   reply    -- the analyst's narrative; replayed to the model as an assistant turn
#   evidence -- raw module output; deliberately NOT replayed (see reconstruct())
#   progress -- the "checking ..." interim note; never replayed
PROP_KEY = 'matterbot_ai'
PROP_REPLY = 'reply'
PROP_EVIDENCE = 'evidence'
PROP_PROGRESS = 'progress'
# Tools spent by a reply, so the per-thread cap survives a restart with no state.
PROP_TOOL_CALLS = 'ai_tool_calls'
# send_message() splits a long reply across several posts. These let reconstruct()
# put it back together as ONE assistant turn (and count its budget once).
PROP_MSG_ID = 'ai_message_id'
PROP_PART = 'ai_part'

# Characters to peel off a token before classifying it. Analysts write prose:
# indicators arrive in backticks, in parentheses, at the end of a sentence.
# Defanging (8.8.8[.]8) puts brackets INSIDE the token, never at the edges, so
# stripping edges is safe -- cmdutils.classify() refangs the rest.
_STRIP = ' \t\r\n`"\'*_,;:!?()<>[]{}.'

# Candidate splitting: whitespace is not enough. "8.8.8.8,evil.example.com" is one
# whitespace token but two indicators.
_CANDIDATE_SPLIT = re.compile(r'[\s,;|]+')
# [label](target) -- consider both halves; the label is often the defanged form.
_MARKDOWN_LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
# "IOC:evil.example.com", "ip=8.8.8.8", "sha256: abcd..."
_LABEL = re.compile(
    r'^(?:ioc|indicator|ip|ipv6|cidr|domain|host|url|hash|md5|sha1|sha256)\s*[:=]\s*',
    re.IGNORECASE,
)
_SCHEMES = ('http://', 'https://', 'hxxp://', 'hxxps://')
# What glues two indicators into one whitespace-free run: "8.8.8.8/1.1.1.1",
# "8.8.8.8->1.1.1.1", "evil[.]example[.]com/path". A bare '/' is also how a URL
# separates host from path, so this only ever gets applied to a token that has
# ALREADY failed to classify as a whole (see _candidates).
_JOIN_SPLIT = re.compile(r'/|->|→')

# Analysts defang (8[.]8[.]8[.]8, hxxps://) and label (IOC:, domain=) things they
# are actually flagging as indicators. Either signal means "trust me, this is
# real" and must bypass the domain-plausibility gate below -- a malicious domain
# in an oddball TLD is exactly the shape a real IOC takes, and dropping it because
# it does not match a known TLD table would be a silent, unexplained refusal.
_DEFANG_HINT = re.compile(r'\[\.\]|\(\.\)|\{\.\}|hxxp', re.IGNORECASE)

# Common gTLDs, including ones heavily abused by malware campaigns precisely
# because they are cheap ("xyz", "top", "click", "icu", ...). Real 2-letter
# ccTLDs (ml, cc, io, ...) do not need to be listed here -- they are covered by
# the generic ccTLD rule in _is_plausible_tld(), unless they collide with a file
# extension below.
_COMMON_TLDS = frozenset({
    'com', 'net', 'org', 'edu', 'gov', 'mil', 'int', 'info', 'biz', 'name', 'pro',
    'mobi', 'asia', 'coop', 'aero', 'museum', 'jobs', 'travel', 'xyz', 'top',
    'club', 'online', 'site', 'store', 'tech', 'app', 'dev', 'page', 'shop',
    'live', 'click', 'link', 'icu', 'cyou', 'buzz', 'fun', 'win', 'bid', 'loan',
    'men', 'work', 'rest', 'vip', 'host', 'press', 'cloud', 'digital', 'systems',
    'solutions', 'email', 'network', 'company', 'group', 'world', 'today', 'life',
})
# File extensions that would otherwise be misread as a domain -- either because
# they collide with a real 2-letter ccTLD (a run-of-the-mill "config.py" would
# otherwise pass as a Paraguayan domain), or because they are just common enough
# in SOC chat ("error.log", "malware.exe") to fire constantly. Checked BEFORE the
# generic ccTLD rule, so the collision always resolves to "not a domain".
_FILE_EXT_BLOCKLIST = frozenset({
    'py', 'sh', 'js', 'md', 'db', 'so', 'rb', 'pl', 'go', 'rs', 'ts', 'cs', 'ps', 'vb',
    'exe', 'dll', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'zip', 'rar',
    'tar', 'gz', 'log', 'txt', 'csv', 'json', 'yml', 'yaml', 'xml', 'html', 'htm',
    'ini', 'cfg', 'conf', 'bak', 'tmp', 'dat', 'bin', 'sys', 'reg', 'bat', 'cmd',
    'ps1', 'vbs', 'jar', 'apk', 'iso', 'dmg', 'msi', 'scr', 'lnk', 'hta', 'pem',
    'crt', 'key', 'sql', 'lock', 'toml', 'class', 'jsp', 'asp', 'aspx', 'php',
})


def _is_plausible_tld(tld):
    """Is `tld` a TLD an analyst would plausibly mean, vs. a file extension?

    cmdutils._HOSTNAME_RE only requires the final label to be alphabetic, so
    "malware.exe" and "it.then" (a run-together sentence) classify as domains
    just as readily as "evil.com" does. This is the gate that tells them apart:
    accept known gTLDs and any 2-letter alphabetic ccTLD (there are ~250 real
    ones, not worth enumerating), but reject the blocklisted extensions first so
    the ccTLD/file-extension collisions (.py/.sh/.md/...) resolve correctly.
    Bias toward accepting when unsure -- see _signals_intent().
    """
    tld = tld.lower()
    if tld in _FILE_EXT_BLOCKLIST:
        return False
    if tld in _COMMON_TLDS:
        return True
    return len(tld) == 2 and tld.isalpha()


def _signals_intent(original_token, candidate):
    """Did the analyst mark `candidate` as an indicator, defanged or labelled?

    A defanged token (brackets, hxxp) or a labelled one (IOC:, domain=) is the
    analyst stating "this is an indicator" in their own words. That statement
    outranks the TLD-plausibility gate: a real malicious domain in an unusual
    TLD must never be silently dropped because it is not in our TLD tables.
    """
    if _DEFANG_HINT.search(candidate):
        return True
    return bool(_LABEL.match(original_token.strip(_STRIP)))


def _candidates(token):
    """Every string worth handing to cmdutils.classify() for one prose token.

    If the token ALREADY classifies as an indicator whole, that is authoritative
    and it is returned alone: a CIDR's network address ("10.0.0.0/8") must not
    also be offered as a second, independent IP, and a defanged URL with a path
    must not also be offered as its bare host. Only a token that does NOT
    classify whole gets split further -- a scheme-less run of two indicators
    glued by '/', '->' or an arrow ("8.8.8.8/1.1.1.1", "8.8.8.8->1.1.1.1", a bare
    host with a URL path) is not itself one indicator, so every resulting
    segment is offered as a candidate and cmdutils.classify() decides, per
    segment, which (if any) are real. A scheme-bearing token that still fails to
    classify is left alone -- a URL's own path is full of '/' and must not be
    torn apart.
    """
    token = token.strip(_STRIP)
    if not token:
        return []
    token = _LABEL.sub('', token).strip(_STRIP)
    if not token:
        return []
    _, indicator_type = cmdutils.classify(token)
    if indicator_type:
        return [token]
    if token.lower().startswith(_SCHEMES):
        return [token]
    segments = [seg.strip(_STRIP) for seg in _JOIN_SPLIT.split(token)]
    segments = [seg for seg in segments if seg]
    return segments or [token]


def extract_indicators(text):
    """Map every indicator in free text to its canonical cmdutils type.

    cmdutils.classify() types one clean token; an analyst hands us a sentence.
    This is the bridge, and it is load-bearing twice over: it builds the
    `authorized` set (what the model is allowed to look up at all) and it decides
    which modules are exposed this turn.

    A domain result additionally passes a plausibility gate (_is_plausible_tld):
    cmdutils._HOSTNAME_RE only requires an alphabetic final label, so ordinary
    prose ("checked it.Then rebooted") and filenames ("malware.exe") classify as
    domains just as readily as real ones do, and SOC chat is full of both. The
    gate is skipped -- accept unconditionally -- when the analyst defanged or
    labelled the token (_signals_intent): that is the analyst stating this is an
    indicator, and a missed real IOC is worse than an admitted filename.
    """
    found = {}
    if not text:
        return found
    # Flatten markdown links so BOTH the label and the target get classified.
    working = _MARKDOWN_LINK.sub(lambda m: f'{m.group(1)} {m.group(2)}', text)
    for token in _CANDIDATE_SPLIT.split(working):
        for candidate in _candidates(token):
            value, indicator_type = cmdutils.classify(candidate)
            if not indicator_type:
                continue
            if indicator_type == cmdutils.DOMAIN and not _signals_intent(token, candidate):
                if not _is_plausible_tld(value.rsplit('.', 1)[-1]):
                    continue
            found[value] = indicator_type
    return found


REDACTED = '<redacted>'

# Credentials in a URL query string -- the exact shape #285/#286 found in
# botscout/proxycheck/mwdb, and the shape a module's SUCCESS output can carry too
# (a "source" link, a cited API URL).
_QUERY_CRED_RE = re.compile(
    r'(?i)([?&](?:api[-_]?key|apikey|key|token|access[-_]?token|auth|secret|password|passwd|pwd)=)'
    r'([^\s&"\'<>]+)'
)
# Labelled secrets anywhere in the text. Deliberately does NOT include a bare
# "key", which appears constantly in legitimate module output ("Key | Value").
_LABELLED_CRED_RE = re.compile(
    r'(?i)\b(api[-_]?key|apikey|access[-_]?token|token|secret|password|passwd)\b(\s*[:=]\s*)'
    r'([^\s"\'<>]{6,})'
)
_BEARER_RE = re.compile(r'(?i)\b(bearer)\s+([A-Za-z0-9._\-]{8,})')


def sanitize_tool_output(text):
    """Strip credentials out of module output before it leaves this process.

    Do NOT rely on the modules for this, and do NOT rely on #286: that fixed the
    exception text of three modules, while a module's *success* output can carry
    a key-bearing source URL just as easily. And unlike an @-command -- whose
    output only ever reaches a Mattermost channel -- the AI ships this text to a
    third-party LLM endpoint. Redact once, here, on the way out.
    """
    if not text:
        return text
    out = _QUERY_CRED_RE.sub(lambda m: f'{m.group(1)}{REDACTED}', text)
    out = _LABELLED_CRED_RE.sub(lambda m: f'{m.group(1)}{m.group(2)}{REDACTED}', out)
    out = _BEARER_RE.sub(lambda m: f'{m.group(1)} {REDACTED}', out)
    return out


def build_tool_definitions(registry, relevant_types):
    """Generate OpenAI-format tool schemas from metadata the modules already carry.

    No new metadata to author: the name is the module name, the description is its
    existing HELP['DEFAULT']['desc'] plus its ACCEPTS types, and the single `query`
    parameter is the indicator.

    Exposure is narrowed to modules that accept an indicator type actually in play.
    No indicators anywhere in the case -> no tools at all, and the model simply
    converses from context. `registry` is expected to be pre-filtered by the
    operator allow-list (see AIAnalyst._registry).
    """
    tools = []
    if not relevant_types:
        return tools
    for name in sorted(registry):
        entry = registry[name] or {}
        if not entry.get('aitool'):
            continue
        accepts = entry.get('accepts')
        if accepts and not set(accepts) & set(relevant_types):
            continue
        help_text = (entry.get('help') or {}).get('DEFAULT') or {}
        desc = help_text.get('desc') or 'No help available.'
        types = ', '.join(accepts) if accepts else cmdutils.TYPES_HUMAN
        tools.append({
            'type': 'function',
            'function': {
                'name': name,
                'description': f'{desc} Accepts: {types}',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': f'the indicator to look up ({types})',
                        },
                    },
                    'required': ['query'],
                },
            },
        })
    return tools
