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
    """Classify operator input into (normalized, endpoint) or (None, None)."""
    if not raw:
        return None, None
    q = raw.strip()
    # Hash check uses the raw token (case-insensitive) — preserve original case.
    if MD5_RE.match(q) or SHA1_RE.match(q) or SHA256_RE.match(q):
        return q.lower(), 'file'
    # For IP/domain checks, normalise to lower + defang restore.
    norm = q.lower().replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    norm = re.sub(r'^(?:https?|hxxps?)://', '', norm)
    # IP check before path-strip (CIDR not supported here, but a bare IP is fine).
    if _is_ip(norm):
        return norm, 'ip'
    norm = norm.split('/', 1)[0]
    if HOSTNAME_RE.match(norm):
        return norm, 'domain'
    return None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/')


def _join_capped(values, cap):
    if not values:
        return None
    values = list(values)
    if len(values) > cap:
        return ', '.join(_cell(v) for v in values[:cap]) + f", …(+{len(values) - cap})"
    return ', '.join(_cell(v) for v in values)


def _format_response(resource, endpoint, data, max_tags, max_judgments):
    """Render a markdown block for a single ThreatBook community response."""
    record = (data or {}).get(resource)
    if not isinstance(record, dict):
        # ThreatBook sometimes nests the resource under a normalised key.
        if isinstance(data, dict) and len(data) == 1:
            record = next(iter(data.values()))
        if not isinstance(record, dict):
            return None

    rows = []
    severity = record.get('severity')
    if severity:
        rows.append(('Severity', severity))

    judgments = record.get('judgments') or []
    joined_judgments = _join_capped(judgments, max_judgments)
    if joined_judgments:
        rows.append(('Judgments', joined_judgments))

    tags_classes = record.get('tags_classes') or []
    # tags_classes is a list of {"tags_type": "...", "tags": [...]} objects.
    flat_tags = []
    for entry in tags_classes:
        if isinstance(entry, dict):
            for tag in entry.get('tags') or []:
                flat_tags.append(tag)
    joined_tags = _join_capped(flat_tags, max_tags)
    if joined_tags:
        rows.append(('Tags', joined_tags))

    basic = record.get('basic') or {}
    if endpoint == 'ip':
        loc = basic.get('location') or {}
        country = loc.get('country')
        if country:
            city = loc.get('city')
            rows.append(('Location', f"{country}{(' / ' + city) if city else ''}"))
        carrier = basic.get('carrier')
        if carrier:
            rows.append(('ASN/Carrier', carrier))
    elif endpoint == 'domain':
        whois = basic.get('whois') or {}
        registrar = whois.get('registrar')
        if registrar:
            rows.append(('Registrar', registrar))
        created = whois.get('creation_date') or whois.get('registered')
        if created:
            rows.append(('Registered', created))

    summary = record.get('summary') or {}
    if endpoint == 'file' and summary:
        threat_level = summary.get('threat_level')
        if threat_level:
            rows.append(('Threat level', threat_level))
        threat_types = summary.get('malware_type') or summary.get('threat_type')
        if threat_types:
            rows.append(('Malware type', _cell(threat_types) if isinstance(threat_types, str) else _join_capped(threat_types, max_tags)))

    if not rows:
        return None

    lines = [f"ThreatBook ({endpoint}) for `{resource}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # Friendly reference URL per endpoint.
    if endpoint == 'ip':
        ref = f"https://x.threatbook.com/v5/ip/{resource}"
    elif endpoint == 'domain':
        ref = f"https://x.threatbook.com/v5/domain/{resource}"
    else:
        ref = f"https://x.threatbook.com/v5/sample/{resource}"
    lines.append(f"| Reference | [ThreatBook]({ref}) |")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    resource, endpoint = _classify(raw)
    if not resource:
        # Silent no-op on shape mismatch — `@ioc` fan-out convention.
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('threatbook', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_tags = int(getattr(settings, 'MAX_TAGS', 20))
    max_judgments = int(getattr(settings, 'MAX_JUDGMENTS', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'ThreatBook is not configured. Set `key` in `settings.py` (free tier at https://threatbook.io/).'}]}

    url = base + endpoint
    try:
        resp = requests.get(
            url,
            params={'apikey': key, 'resource': resource},
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot ThreatBook module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        # Note: the apikey is in the query string. Don't echo the URL.
        log.exception("threatbook request failed")
        return {'messages': [{'text': f"ThreatBook request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'ThreatBook: authentication failed or quota exhausted — check the API key and free-tier limits.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"ThreatBook: no record for `{resource}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"ThreatBook returned HTTP {resp.status_code} for `{endpoint}`."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("threatbook returned non-JSON")
        return {'messages': [{'text': 'ThreatBook returned a non-JSON response.'}]}

    rc = payload.get('response_code')
    if rc != 0:
        verbose = payload.get('verbose_msg') or 'unknown error'
        # rc=-3 = invalid input, rc=-4 = quota exceeded, rc=-1 = no record, etc.
        if rc == -1:
            return {'messages': [{'text': f"ThreatBook: no record for `{resource}`."}]}
        return {'messages': [{'text': f"ThreatBook error (code `{rc}`): {_cell(verbose)}"}]}

    text = _format_response(resource, endpoint, payload.get('data'), max_tags, max_judgments)
    if not text:
        return {'messages': [{'text': f"ThreatBook: empty record for `{resource}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
