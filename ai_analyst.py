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


def _candidates(token):
    """Every string worth handing to cmdutils.classify() for one prose token."""
    token = token.strip(_STRIP)
    if not token:
        return []
    token = _LABEL.sub('', token).strip(_STRIP)
    if not token:
        return []
    out = [token]
    # A bare host with a path ("evil[.]example[.]com/path") is not a URL -- it has
    # no scheme -- and would classify as nothing. The host still is an indicator.
    if '/' in token and not token.lower().startswith(_SCHEMES):
        head = token.split('/', 1)[0].strip(_STRIP)
        if head:
            out.append(head)
    return out


def extract_indicators(text):
    """Map every indicator in free text to its canonical cmdutils type.

    cmdutils.classify() types one clean token; an analyst hands us a sentence.
    This is the bridge, and it is load-bearing twice over: it builds the
    `authorized` set (what the model is allowed to look up at all) and it decides
    which modules are exposed this turn.
    """
    found = {}
    if not text:
        return found
    # Flatten markdown links so BOTH the label and the target get classified.
    working = _MARKDOWN_LINK.sub(lambda m: f'{m.group(1)} {m.group(2)}', text)
    for token in _CANDIDATE_SPLIT.split(working):
        for candidate in _candidates(token):
            value, indicator_type = cmdutils.classify(candidate)
            if indicator_type:
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
