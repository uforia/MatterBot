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
    """Return (normalized, endpoint, label) or (None, None, None).

    Kaspersky OpenTIP exposes /search/{ip,domain,url,hash}.
    """
    if not raw:
        return None, None, None
    q = raw.strip()

    # Hash family is checked first (case-insensitive, normalised to lower).
    if SHA256_RE.match(q):
        return q.lower(), 'hash', 'SHA256'
    if SHA1_RE.match(q):
        return q.lower(), 'hash', 'SHA1'
    if MD5_RE.match(q):
        return q.lower(), 'hash', 'MD5'

    # URL detection — requires explicit scheme (defang-restored).
    norm = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    if re.match(r'^hxxps?://', norm, re.IGNORECASE):
        norm = re.sub(r'^hxxps?://', lambda m: m.group(0).lower().replace('hxxp', 'http'), norm, flags=re.IGNORECASE)
    if norm.lower().startswith(('http://', 'https://')):
        return norm, 'url', 'URL'

    # IP / domain — strip URL path before hostname check (CIDR rejected).
    norm_l = norm.lower()
    if _is_ip(norm_l):
        return norm_l, 'ip', 'IP'
    norm_l = norm_l.split('/', 1)[0]
    if HOSTNAME_RE.match(norm_l):
        return norm_l, 'domain', 'domain'
    return None, None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format_zone_emoji(zone):
    """Map Kaspersky verdict zone to a short prefix. Kept ASCII so the
    table cell renders cleanly across Mattermost themes."""
    return {
        'Green': 'safe',
        'Yellow': 'suspicious',
        'Red': 'malicious',
        'Grey': 'unknown',
        'Unknown': 'unknown',
    }.get(zone, str(zone) if zone else 'unknown')


def _format(query, label, endpoint, payload, max_detections, max_categories):
    if not isinstance(payload, dict):
        return None

    zone = payload.get('Zone')
    rows = [
        ('Query', f"{query} ({label})"),
        ('Verdict zone', f"{zone or 'Unknown'} ({_format_zone_emoji(zone)})"),
    ]

    # Endpoint-specific summary fields.
    if endpoint == 'hash':
        info = payload.get('FileGeneralInfo') or {}
        if isinstance(info, dict):
            for k_in, k_out in [
                ('FileStatus', 'File status'),
                ('Type', 'File type'),
                ('Size', 'File size'),
                ('Signer', 'Signer'),
                ('Packer', 'Packer'),
                ('FirstSeen', 'First seen'),
                ('LastSeen', 'Last seen'),
                ('HitsCount', 'Hits count'),
                ('Md5', 'MD5'),
                ('Sha1', 'SHA1'),
                ('Sha256', 'SHA256'),
            ]:
                v = info.get(k_in)
                if v is not None and v != '':
                    rows.append((k_out, v))
    elif endpoint == 'ip':
        info = payload.get('IpGeneralInfo') or {}
        if isinstance(info, dict):
            for k_in, k_out in [
                ('CountryCode', 'Country'),
                ('Ip', 'IP'),
                ('Status', 'Status'),
                ('HitsCount', 'Hits count'),
                ('FirstSeen', 'First seen'),
                ('LastSeen', 'Last seen'),
            ]:
                v = info.get(k_in)
                if v is not None and v != '':
                    rows.append((k_out, v))
    elif endpoint == 'domain':
        info = payload.get('DomainGeneralInfo') or {}
        if isinstance(info, dict):
            for k_in, k_out in [
                ('Domain', 'Domain'),
                ('Ipv4Count', 'IPv4 count'),
                ('FilesCount', 'File count'),
                ('UrlsCount', 'URL count'),
                ('HitsCount', 'Hits count'),
                ('FirstSeen', 'First seen'),
                ('LastSeen', 'Last seen'),
            ]:
                v = info.get(k_in)
                if v is not None and v != '':
                    rows.append((k_out, v))
    elif endpoint == 'url':
        info = payload.get('UrlGeneralInfo') or {}
        if isinstance(info, dict):
            for k_in, k_out in [
                ('Url', 'URL'),
                ('Host', 'Host'),
                ('Ipv4Count', 'Resolved IP count'),
                ('FilesCount', 'Linked file count'),
            ]:
                v = info.get(k_in)
                if v is not None and v != '':
                    rows.append((k_out, v))

    # Categories — flat string list across all endpoints when present.
    categories = payload.get('Categories') or []
    if isinstance(categories, list) and categories:
        shown_cats = categories[:max_categories]
        cats_str = ', '.join(_cell(c) for c in shown_cats)
        if len(categories) > max_categories:
            cats_str += f", …(+{len(categories) - max_categories} more)"
        rows.append(('Categories', cats_str))

    lines = [f"Kaspersky OpenTIP record for `{query}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # Detections sub-table (hash endpoint, sometimes URL too).
    detections = payload.get('DetectionsInfo') or payload.get('Detections') or []
    if isinstance(detections, list) and detections:
        total = len(detections)
        shown = detections[:max_detections]
        lines.append('')
        lines.append(f"**Detections ({len(shown)} of {total}):**")
        lines.append('| Type | Description | LastDetectDate |')
        lines.append('| :- | :- | :- |')
        for d in shown:
            if not isinstance(d, dict):
                continue
            dtype = d.get('DetectionMethod') or d.get('Type') or '?'
            desc = d.get('DescriptionUrl') or d.get('Name') or d.get('Description') or ''
            date = d.get('LastDetectDate') or d.get('Date') or ''
            lines.append(f"| `{_cell(dtype)}` | `{_cell(desc)}` | `{_cell(date)}` |")
        if total > max_detections:
            lines.append(f"_…{total - max_detections} more detection(s) not shown._")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    query, endpoint, label = _classify(params[0])
    if not query:
        # Silent no-op on shape mismatch (matches the rest of the TI modules).
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('kaspersky', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_detections = int(getattr(settings, 'MAX_DETECTIONS', 10))
    max_categories = int(getattr(settings, 'MAX_CATEGORIES', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'Kaspersky OpenTIP is not configured. Set `key` in `settings.py` (free at https://opentip.kaspersky.com/).'}]}

    url = base + 'search/' + endpoint
    headers = {
        'x-api-key': key,
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Kaspersky OpenTIP module',
    }

    try:
        resp = requests.get(
            url,
            params={'request': query},
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("kaspersky request failed")
        return {'messages': [{'text': f"Kaspersky OpenTIP request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Kaspersky OpenTIP: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Kaspersky OpenTIP: rate-limited (HTTP 429). Free tier daily quota may be exhausted.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"Kaspersky OpenTIP: no record for `{query}` ({label})."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Kaspersky OpenTIP returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("kaspersky returned non-JSON")
        return {'messages': [{'text': 'Kaspersky OpenTIP returned a non-JSON response.'}]}

    text = _format(query, label, endpoint, payload, max_detections, max_categories)
    if not text:
        return {'messages': [{'text': f"Kaspersky OpenTIP: unrecognised response shape for `{query}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
