#!/usr/bin/env python3

import ipaddress
import re
import requests

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

HOSTNAME_RE = re.compile(
    r'^(?=.{1,253}$)'
    r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)\.)+'
    r'[a-zA-Z]{2,63}$'
)
MD5_RE = re.compile(r'^[A-Fa-f0-9]{32}$')
SHA1_RE = re.compile(r'^[A-Fa-f0-9]{40}$')
SHA256_RE = re.compile(r'^[A-Fa-f0-9]{64}$')


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _classify(raw):
    """Return (normalized, type, label) or (None, None, None).

    Type strings follow ThreatRip's documented vocabulary: 'ip', 'domain',
    'url', 'hash' (the API typically dispatches MD5/SHA1/SHA256 from a
    single hash endpoint).
    """
    if not raw:
        return None, None, None
    q = raw.strip()
    if SHA256_RE.match(q):
        return q.lower(), 'hash', 'SHA256'
    if SHA1_RE.match(q):
        return q.lower(), 'hash', 'SHA1'
    if MD5_RE.match(q):
        return q.lower(), 'hash', 'MD5'

    norm = q.lower().replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    if re.match(r'^hxxps?://', norm):
        norm = norm.replace('hxxps://', 'https://', 1).replace('hxxp://', 'http://', 1)
    if norm.startswith(('http://', 'https://')):
        return norm, 'url', 'URL'

    if _is_ip(norm):
        return norm, 'ip', 'IP'
    norm = norm.split('/', 1)[0]
    if HOSTNAME_RE.match(norm):
        return norm, 'domain', 'domain'
    return None, None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _extract_record(payload):
    """ThreatRip wraps the record differently across endpoints — accept the
    common shapes (direct, `data`, `result`, single-element list)."""
    if not isinstance(payload, dict):
        if isinstance(payload, list) and payload:
            first = payload[0]
            return first if isinstance(first, dict) else None
        return None
    for key in ('data', 'result', 'record', 'indicator'):
        v = payload.get(key)
        if isinstance(v, dict):
            return v
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v[0]
    # Already the record itself.
    return payload


def _format(query, label, ttype, payload, max_tags):
    record = _extract_record(payload)
    if not isinstance(record, dict):
        return None

    rows = [('Query', f"{query} ({label})")]

    severity = record.get('severity') or record.get('verdict') or record.get('classification')
    if severity:
        rows.append(('Severity', severity))
    score = record.get('score') or record.get('risk_score') or record.get('risk')
    if isinstance(score, dict):
        score = score.get('value') or score.get('score')
    if score is not None:
        rows.append(('Risk score', score))

    first = record.get('first_seen') or record.get('firstSeen') or record.get('seen_first')
    last = record.get('last_seen') or record.get('lastSeen') or record.get('seen_last')
    if first:
        rows.append(('First seen', first))
    if last:
        rows.append(('Last seen', last))

    actor = record.get('actor') or record.get('threat_actor') or record.get('attributed_actor')
    if isinstance(actor, list):
        actor = ', '.join(str(a) for a in actor[:5])
    if actor:
        rows.append(('Actor', actor))
    campaign = record.get('campaign') or record.get('campaigns')
    if isinstance(campaign, list):
        campaign = ', '.join(str(c) for c in campaign[:5])
    if campaign:
        rows.append(('Campaign', campaign))
    malware = record.get('malware') or record.get('malware_family') or record.get('family')
    if isinstance(malware, list):
        malware = ', '.join(str(m) for m in malware[:5])
    if malware:
        rows.append(('Malware', malware))

    tags = record.get('tags') or record.get('labels') or []
    if isinstance(tags, list) and tags:
        shown_tags = tags[:max_tags]
        tag_str = ', '.join(_cell(str(t)) for t in shown_tags)
        if len(tags) > max_tags:
            tag_str += f", …(+{len(tags) - max_tags})"
        rows.append(('Tags', tag_str))

    # _cell() strips backticks so a backtick in the URL-classified query
    # can't close the inline-code wrap around the heading.
    lines = [f"ThreatRip record for `{_cell(query)}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(_trim(v, 200))}` |")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    query, ttype, label = _classify(params[0])
    if not query:
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('threatrip', {})
    url_pattern = cfg.get('url_pattern') or 'https://api.threat.rip/v1/{type}/{value}'
    key = cfg.get('key') or ''
    max_tags = int(getattr(settings, 'MAX_TAGS', 15))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'ThreatRip is not configured. Set `key` in `settings.py` (https://www.threat.rip/).'}]}

    # Two-step substitution so a stray brace in `value` (after urlencoding it
    # shouldn't be possible, but defence-in-depth) cannot consume the `{type}`
    # placeholder. Type comes from the trusted SUBCOMMANDS-style vocabulary,
    # value is urlencoded before substitution.
    url = url_pattern.replace('{type}', ttype).replace('{value}', requests.utils.quote(query, safe=''))

    headers = {
        'Authorization': f'Bearer {key}',
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot ThreatRip module',
    }

    try:
        resp = requests.get(url, headers=headers, allow_redirects=False, timeout=(10, 30))
    except requests.RequestException as e:
        log.exception("threatrip request failed")
        return {'messages': [{'text': f"ThreatRip request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'ThreatRip: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'ThreatRip: rate-limited (HTTP 429).'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"ThreatRip: no record for `{query}` ({label})."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"ThreatRip returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("threatrip returned non-JSON")
        return {'messages': [{'text': 'ThreatRip returned a non-JSON response.'}]}

    text = _format(query, label, ttype, payload, max_tags)
    if not text:
        return {'messages': [{'text': f"ThreatRip: unrecognised response shape for `{query}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
