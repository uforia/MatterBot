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

    Endpoint values are MetaDefender v4 path segments: 'hash', 'ip', 'domain'.
    """
    if not raw:
        return None, None, None
    q = raw.strip()
    for r, label in [(MD5_RE, 'MD5'), (SHA1_RE, 'SHA1'), (SHA256_RE, 'SHA256')]:
        if r.match(q):
            return q.lower(), 'hash', label

    norm = q.lower().replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    norm = re.sub(r'^(?:https?|hxxps?)://', '', norm)
    if _is_ip(norm):
        return norm, 'ip', 'IP'
    norm = norm.split('/', 1)[0]
    if HOSTNAME_RE.match(norm):
        return norm, 'domain', 'domain'
    return None, None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format_hash(query, label, payload, max_engines):
    if not isinstance(payload, dict):
        return None
    file_info = payload.get('file_info') or {}
    scan = payload.get('scan_results') or {}

    rows = [('Query', f"{query} ({label})")]
    if file_info.get('file_type_description'):
        rows.append(('File type', file_info['file_type_description']))
    if file_info.get('file_size') is not None:
        rows.append(('File size', file_info['file_size']))
    if scan.get('scan_all_result_a'):
        rows.append(('Verdict', scan['scan_all_result_a']))
    if scan.get('total_detected_avs') is not None and scan.get('total_avs') is not None:
        rows.append(('Detection ratio', f"{scan['total_detected_avs']} / {scan['total_avs']}"))
    if scan.get('start_time'):
        rows.append(('Scan start', scan['start_time']))

    lines = [f"MetaDefender hash record for `{query}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    sha256 = file_info.get('sha256') or query
    lines.append(f"| Reference | [MetaDefender hash report](https://metadefender.opswat.com/results/file/{sha256}/hash/overview) |")

    # Engine detections: scan_results.scan_details is a dict {engine: {…}}.
    engines = scan.get('scan_details')
    if isinstance(engines, dict) and engines:
        # Surface only engines with a positive detection (threat_found is set).
        detected = [(name, d) for name, d in engines.items()
                    if isinstance(d, dict) and d.get('threat_found')]
        if detected:
            total = len(detected)
            shown = detected[:max_engines]
            lines.append('')
            lines.append(f"**Engine detections ({len(shown)} of {total}):**")
            lines.append('| Engine | Threat | Scan time |')
            lines.append('| :- | :- | :- |')
            for name, d in shown:
                lines.append(f"| `{_cell(name)}` | `{_cell(d.get('threat_found', '?'))}` | `{_cell(d.get('scan_time', '?'))}` |")
            if total > max_engines:
                lines.append(f"_…{total - max_engines} more engine(s) flagged but not shown._")
    return '\n'.join(lines)


def _format_ip_or_domain(query, label, endpoint, payload, max_sources):
    if not isinstance(payload, dict):
        return None
    rows = [('Query', f"{query} ({label})")]

    address = payload.get('address') or payload.get('lookup_results') or {}
    if isinstance(address, dict):
        country = address.get('country') or (payload.get('geo_info') or {}).get('country') or {}
        if isinstance(country, dict):
            country = country.get('name')
        if country:
            rows.append(('Country', country))

    geo = payload.get('geo_info') or {}
    if isinstance(geo, dict):
        org = geo.get('organization') or geo.get('asn_name')
        asn = geo.get('asn')
        if org:
            rows.append(('Organisation', org))
        if asn:
            rows.append(('ASN', asn))

    # Source detections live in lookup_results.sources (v4 IP/domain shape).
    lookup = payload.get('lookup_results') or {}
    sources = lookup.get('sources') if isinstance(lookup, dict) else None
    detected_by = lookup.get('detected_by') if isinstance(lookup, dict) else None
    if detected_by is not None:
        rows.append(('Detected by', detected_by))

    lines = [f"MetaDefender {endpoint} record for `{query}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")
    portal = f"https://metadefender.opswat.com/threat-intelligence-feeds/{endpoint}/{query}"
    lines.append(f"| Reference | [MetaDefender {endpoint} report]({portal}) |")

    if isinstance(sources, list) and sources:
        total = len(sources)
        shown = sources[:max_sources]
        lines.append('')
        lines.append(f"**Detection sources ({len(shown)} of {total}):**")
        lines.append('| Provider | Status | Update | Detail |')
        lines.append('| :- | :- | :- | :- |')
        for s in shown:
            if not isinstance(s, dict):
                continue
            provider = s.get('provider') or s.get('source') or '?'
            status = s.get('status') if 'status' in s else s.get('assessment', '?')
            update = s.get('update_time') or s.get('updated') or ''
            detail = s.get('detail') or s.get('category') or s.get('detection') or ''
            lines.append(f"| `{_cell(provider)}` | `{_cell(status)}` | `{_cell(update)}` | `{_cell(detail)}` |")
        if total > max_sources:
            lines.append(f"_…{total - max_sources} more source(s) not shown._")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    query, endpoint, label = _classify(params[0])
    if not query:
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('metadefender', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_engines = int(getattr(settings, 'MAX_ENGINES', 8))
    max_sources = int(getattr(settings, 'MAX_SOURCES', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'MetaDefender is not configured. Set `key` in `settings.py` (free at https://metadefender.opswat.com/).'}]}

    url = base + endpoint + '/' + requests.utils.quote(query, safe='')
    headers = {
        'apikey': key,
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot MetaDefender module',
    }

    try:
        resp = requests.get(url, headers=headers, allow_redirects=False, timeout=(10, 30))
    except requests.RequestException as e:
        log.exception("metadefender request failed")
        return {'messages': [{'text': f"MetaDefender request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'MetaDefender: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'MetaDefender: rate-limited (HTTP 429). Free-tier quota may be exhausted.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"MetaDefender: no record for `{query}` ({label})."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"MetaDefender returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("metadefender returned non-JSON")
        return {'messages': [{'text': 'MetaDefender returned a non-JSON response.'}]}

    if endpoint == 'hash':
        text = _format_hash(query, label, payload, max_engines)
    else:
        text = _format_ip_or_domain(query, label, endpoint, payload, max_sources)

    if not text:
        return {'messages': [{'text': f"MetaDefender: unrecognised response shape for `{query}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
