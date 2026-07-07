#!/usr/bin/env python3

import ipaddress
import re
import requests

from matterbot_formatting import sanitize_block, sanitize_inline

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
import logging

log = logging.getLogger('MatterBot')
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here


def _wrap_output(header, body):
    """Wrap hackertarget output: the tool body goes inside a code fence via
    sanitize_block. The caller builds the header and sanitizes its interpolated
    subject with sanitize_inline before passing it in."""
    return f"{header}\n```\n{sanitize_block(body)}\n```"

HOSTNAME_RE = re.compile(
    r'^(?=.{1,253}$)'
    r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)\.)+'
    r'[a-zA-Z]{2,63}$'
)


def _validate_domain(raw):
    if not raw:
        return None
    q = raw.strip().lower()
    q = q.replace('[.]', '.').replace('(.)', '.')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    return q if HOSTNAME_RE.match(q) else None


def _validate_ip(raw):
    if not raw:
        return None
    q = raw.strip()
    q = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    try:
        return str(ipaddress.ip_address(q))
    except ValueError:
        return None


def _validate_domain_or_ip(raw):
    return _validate_domain(raw) or _validate_ip(raw)


# Each subcommand declares its endpoint, the operator-facing label, and the
# validator that gates input before it's interpolated into the URL.
SUBCOMMANDS = {
    'dns':        {'endpoint': 'dnslookup',     'label': 'DNS records',           'validator': _validate_domain},
    'rdns':       {'endpoint': 'reversedns',    'label': 'reverse DNS',           'validator': _validate_ip},
    'subdomains': {'endpoint': 'hostsearch',    'label': 'subdomain enumeration', 'validator': _validate_domain},
    'whois':      {'endpoint': 'whois',         'label': 'WHOIS',                 'validator': _validate_domain},
    'geoip':      {'endpoint': 'geoip',         'label': 'GeoIP',                 'validator': _validate_ip},
    'asn':        {'endpoint': 'aslookup',      'label': 'AS lookup',             'validator': _validate_ip},
    'mtr':        {'endpoint': 'mtr',           'label': 'MTR trace',             'validator': _validate_domain_or_ip},
    'shareddns':  {'endpoint': 'findshareddns', 'label': 'shared DNS',            'validator': _validate_domain},
}

# Hackertarget surfaces failure conditions as plain-text bodies that begin
# with one of these prefixes. We use them to switch from "render as data"
# to "render as error".
ERROR_PREFIXES = (
    'error',
    'API count exceeded',
    'invalid',
)


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _looks_like_error(body):
    head = body.strip().splitlines()[0] if body else ''
    head_l = head.lower()
    return any(p.lower() in head_l for p in ERROR_PREFIXES) or head.startswith('error')


def _usage():
    cmds = ', '.join(f"`{k}`" for k in SUBCOMMANDS)
    return (
        "Usage: `@hackertarget <subcommand> <target>`\n"
        f"Subcommands: {cmds}\n"
        "Example: `@hackertarget subdomains paypal.com`"
    )


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': _usage()}]}

    sub = params[0].lower().strip()
    if sub not in SUBCOMMANDS:
        # Silent no-op rather than rejection — the operator may have meant a
        # different module. Usage hint only fires when params is empty.
        return {'messages': messages}

    if len(params) < 2:
        return {'messages': [{'text': f"Usage: `@hackertarget {sub} <target>` ({SUBCOMMANDS[sub]['label']})"}]}

    target = params[1]
    cfg = SUBCOMMANDS[sub]
    normalized = cfg['validator'](target)
    if not normalized:
        return {'messages': [{'text': f"hackertarget {sub}: `{_cell(target)}` is not a valid target for {cfg['label']}."}]}

    api = getattr(settings, 'APIURL', {}).get('hackertarget', {})
    base = (api.get('url') or '').rstrip('/') + '/'
    key = api.get('key') or ''
    max_lines = int(getattr(settings, 'MAX_LINES', 60))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    url = base + cfg['endpoint']
    headers = {
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Hackertarget module',
    }
    if key and not key.startswith('<'):
        # Paid-tier auth: bearer token. Free tier needs no header.
        headers['Authorization'] = f'Bearer {key}'

    try:
        resp = requests.get(
            url,
            params={'q': normalized},
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("hackertarget request failed (%s)", cfg['endpoint'])
        return {'messages': [{'text': f"hackertarget {sub} request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'hackertarget: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'hackertarget: rate-limited (HTTP 429). Free tier is ~50 queries/day per source IP.'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"hackertarget {sub} returned HTTP {resp.status_code}."}]}

    body = (resp.text or '').strip()
    if not body:
        return {'messages': [{'text': f"hackertarget {sub}: empty response for `{normalized}`."}]}

    if _looks_like_error(body):
        # Surface the first line; cap to keep error noise bounded.
        first = body.splitlines()[0].strip()
        return {'messages': [{'text': f"hackertarget {sub}: `{_cell(first[:300])}`"}]}

    # Truncate to MAX_LINES with footer; then truncate to MAX_OUTPUT_CHARS.
    lines = body.splitlines()
    total = len(lines)
    truncated_lines = total > max_lines
    rendered_body = '\n'.join(lines[:max_lines])
    if truncated_lines:
        rendered_body += f"\n…({total - max_lines} more line(s) omitted)"

    header = f"**hackertarget {sub}** ({cfg['label']}) for `{sanitize_inline(normalized)}`:"
    text = _wrap_output(header, rendered_body)
    if len(text) > max_chars:
        # Pull back inside the code fence so the closing ``` survives.
        head_room = max_chars - len(header) - len('\n```\n\n```\n_…output truncated._')
        if head_room > 0:
            text = _wrap_output(header, rendered_body[:head_room]) + "\n_…output truncated._"

    messages.append({'text': text})
    return {'messages': messages}
