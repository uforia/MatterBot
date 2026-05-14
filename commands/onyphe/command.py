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


def _validate_domain(raw):
    if not raw:
        return None
    q = raw.strip().lower()
    q = q.replace('[.]', '.').replace('(.)', '.')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    return q if HOSTNAME_RE.match(q) else None


def _validate_ip_or_domain(raw):
    return _validate_ip(raw) or _validate_domain(raw)


# Subcommand → (endpoint segment, validator, label).
SUBCOMMANDS = {
    'summary':    ('summary/ip',          _validate_ip,           'IP summary'),
    'resolver':   ('simple/resolver',     _validate_ip_or_domain, 'DNS resolver'),
    'threatlist': ('simple/threatlist',   _validate_ip,           'threat-list membership'),
    'ctl':        ('simple/ctl',          _validate_domain,       'Certificate Transparency'),
    'datascan':   ('simple/datascan',     _validate_ip,           'surface scan'),
}


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format_summary_header(target, payload, label):
    """Header row + total/page metadata common to every Onyphe response shape."""
    lines = [f"Onyphe {label} for `{target}`:"]
    if not isinstance(payload, dict):
        return lines
    error = payload.get('error')
    text = payload.get('text')
    if error and error != 0:
        lines.append(f"_Onyphe error {error}: {_cell(text or 'no detail')}._")
    total = payload.get('total')
    if total is not None:
        lines.append(f"_Total results: {total}_")
    return lines


def _format_records(results, max_records):
    """Render the records list as a markdown table with per-record category."""
    if not isinstance(results, list) or not results:
        return ['_No records returned._']
    total = len(results)
    truncated = total > max_records
    shown = results[:max_records]

    # Pick the most relevant columns based on what's present across records.
    candidate_columns = ['@category', '@timestamp', 'ip', 'port', 'protocol',
                         'subnet', 'asn', 'country', 'organization', 'app',
                         'forward', 'reverse', 'host', 'domain', 'subject',
                         'fingerprint', 'threatlist', 'tag']
    present = []
    for col in candidate_columns:
        if any(isinstance(r, dict) and r.get(col) for r in shown):
            present.append(col)
        if len(present) >= 5:
            break

    if not present:
        # Fall back to a key dump if none of the well-known columns appear.
        present = list({k for r in shown if isinstance(r, dict) for k in r.keys()})[:5]

    lines = ['| ' + ' | '.join(present) + ' |']
    lines.append('| ' + ' | '.join([':-'] * len(present)) + ' |')
    for r in shown:
        if not isinstance(r, dict):
            continue
        row = []
        for col in present:
            v = r.get(col)
            if isinstance(v, (list, tuple)):
                v = ', '.join(str(x) for x in v[:3])
                if isinstance(r.get(col), (list, tuple)) and len(r[col]) > 3:
                    v += f", …(+{len(r[col]) - 3})"
            row.append(f"`{_cell(v) if v is not None else '—'}`")
        lines.append('| ' + ' | '.join(row) + ' |')
    if truncated:
        lines.append(f"_…{total - max_records} more record(s) not shown._")
    return lines


def _format(target, label, payload, max_records):
    if not isinstance(payload, dict):
        return None
    lines = _format_summary_header(target, payload, label)
    results = payload.get('results') or []
    if results:
        lines.append('')
        lines.extend(_format_records(results, max_records))
    elif not any('error' in line.lower() for line in lines[1:]):
        lines.append('_No records returned._')
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{
            'text': "Usage: `@onyphe [summary|resolver|threatlist|ctl|datascan] <target>` — bare `@onyphe <ip>` → summary."
        }]}

    # Subcommand vs. bare-IP. If the first arg is a known subcommand AND
    # there's a target after it, use it; otherwise treat the first arg as the
    # target for `summary`.
    sub = None
    target = None
    if params[0].lower() in SUBCOMMANDS and len(params) >= 2:
        sub = params[0].lower()
        target = params[1]
    else:
        sub = 'summary'
        target = params[0]

    endpoint, validator, label = SUBCOMMANDS[sub]
    normalized = validator(target)
    if not normalized:
        # Silent no-op only if subcommand wasn't explicit — otherwise be
        # explicit about the rejection so the operator knows their subcommand
        # got the wrong target shape.
        if params[0].lower() in SUBCOMMANDS:
            return {'messages': [{'text': f"onyphe {sub}: `{_cell(target)}` is not a valid target for {label}."}]}
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('onyphe', {})
    token = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_records = int(getattr(settings, 'MAX_RECORDS', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not token or token.startswith('<'):
        return {'messages': [{'text': 'Onyphe is not configured. Set `key` in `settings.py` (free tier at https://www.onyphe.io/).'}]}

    url = base + endpoint + '/' + requests.utils.quote(normalized, safe='')
    headers = {
        'Authorization': f'bearer {token}',
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Onyphe module',
    }

    try:
        resp = requests.get(url, headers=headers, allow_redirects=False, timeout=(10, 30))
    except requests.RequestException as e:
        log.exception("onyphe request failed")
        return {'messages': [{'text': f"Onyphe request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Onyphe: authentication failed — check the API token.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Onyphe: rate-limited (HTTP 429). Free-tier quota may be exhausted.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"Onyphe: no record for `{normalized}` ({label})."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Onyphe returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("onyphe returned non-JSON")
        return {'messages': [{'text': 'Onyphe returned a non-JSON response.'}]}

    text = _format(normalized, label, payload, max_records)
    if not text:
        return {'messages': [{'text': f"Onyphe: unrecognised response shape for `{normalized}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
