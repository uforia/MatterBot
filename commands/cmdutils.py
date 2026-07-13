#!/usr/bin/env python3

"""Shared helpers for command modules.

The commands side had no shared module -- every module that needed to work out
"is this string an IP, a domain, a URL, or a file hash?" hand-rolled its own
classifier. Five of them already had, and had already drifted into different
return shapes and vocabularies. This is the one place that logic should live.

`classify()` answers the *canonical* question -- what kind of indicator is this,
in a fixed vocabulary. It deliberately does NOT know how any particular vendor's
API names or routes that type; that mapping is genuinely per-module and stays in
the module. A module keeps its own tiny `type -> endpoint` table and calls this
for the detection half.

`accepts()` is the dispatch-side gate: a command that declares `ACCEPTS` in its
defaults is only run when the indicator matches. A command that declares nothing
accepts anything, so this is backwards-compatible and adopted per module. That
is what stops `@ioc 8.8.8.8` fanning an IP out to domain-only and hash-only
modules, each of which would otherwise answer with an error in the channel.

Kept import-light (stdlib only) so it runs under the dependency-free test
runner, like feedutils on the feeds side.
"""

import ipaddress
import re

# The canonical indicator vocabulary. A module's ACCEPTS lists a subset of these.
IP = 'ip'
IPV6 = 'ipv6'
DOMAIN = 'domain'
URL = 'url'
MD5 = 'md5'
SHA1 = 'sha1'
SHA256 = 'sha256'

TYPES = (IP, IPV6, DOMAIN, URL, MD5, SHA1, SHA256)

# A human-readable list for the "that is not something I can look up" reply.
TYPES_HUMAN = 'an IP, IPv6 address, domain, URL, or file hash (MD5/SHA1/SHA256)'

_MD5_RE = re.compile(r'^[A-Fa-f0-9]{32}$')
_SHA1_RE = re.compile(r'^[A-Fa-f0-9]{40}$')
_SHA256_RE = re.compile(r'^[A-Fa-f0-9]{64}$')
_HOSTNAME_RE = re.compile(
    r'^(?=.{1,253}$)'
    r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)\.)+'
    r'[a-zA-Z]{2,63}$'
)


def _refang(value):
    """Undo the common IoC defang tricks so a pasted indicator still classifies.

    Threat-intel indicators are routinely shared defanged (hxxp://, 8[.]8[.]8[.]8)
    so they are not clickable. A user pasting one after @ioc means the indicator,
    not a typo -- refang before classifying, and hand the refanged form back.
    """
    out = value.replace('[.]', '.').replace('(.)', '.').replace('{.}', '.')
    out = out.replace('[:]', ':').replace('[@]', '@').replace('(@)', '@')
    if out[:8].lower().startswith(('hxxps://', 'hxxp://')):
        out = re.sub(r'(?i)^hxxp', 'http', out, count=1)
    return out


def classify(value):
    """Return (normalized_value, canonical_type), or (value, None) if unknown.

    The type is one of TYPES. `None` means the string is not a recognisable
    indicator at all (a free-text query, a typo). Detection order matters: a
    64-hex string is a SHA256, never a domain, so hashes are checked first.
    """
    if value is None:
        return None, None
    raw = value.strip()
    if not raw:
        return raw, None

    # Hashes: an unadorned hex token of the right length. Check before anything
    # else, since these can never be a hostname or IP.
    if _SHA256_RE.match(raw):
        return raw.lower(), SHA256
    if _SHA1_RE.match(raw):
        return raw.lower(), SHA1
    if _MD5_RE.match(raw):
        return raw.lower(), MD5

    norm = _refang(raw)

    # URL: keep the scheme; anything with an http(s) scheme is a URL, not a host.
    if norm[:8].lower().startswith(('http://', 'https://')):
        return norm, URL

    # IP (v4 or v6) before hostname -- an IP literal is never a hostname.
    try:
        addr = ipaddress.ip_address(norm)
        return norm, IPV6 if isinstance(addr, ipaddress.IPv6Address) else IP
    except ValueError:
        pass

    if _HOSTNAME_RE.match(norm):
        return norm.lower(), DOMAIN

    return raw, None


def accepts(command_entry, indicator_type):
    """Whether a command should run for an indicator of `indicator_type`.

    `command_entry` is the per-command dict the loader builds (it may carry an
    'accepts' list). The contract is opt-in and fail-open:

    - No 'accepts' declared -> True. The command takes anything (free-text args,
      or it simply has not been annotated yet). This is what keeps the change
      backwards-compatible and incrementally adoptable.
    - 'accepts' declared -> run only when the indicator type is in it. An
      unclassifiable indicator (indicator_type is None) matches nothing, so a
      type-aware command is correctly skipped rather than handed a junk value.
    """
    declared = command_entry.get('accepts') if command_entry else None
    if not declared:
        return True
    return indicator_type in declared


def normalise_accepts(value):
    """Validate a module's ACCEPTS declaration into a list of known types, or None.

    A misspelled or non-list ACCEPTS should not silently filter a module down to
    nothing (which would make it look broken); treat anything unusable as "not
    declared" -> accept-anything, the safe default. Unknown type strings are
    dropped so a typo like 'ipv4' cannot make a rule that never matches.
    """
    if not value or not isinstance(value, (list, tuple, set)):
        return None
    known = [t for t in value if t in TYPES]
    return known or None
