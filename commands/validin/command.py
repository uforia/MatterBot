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


def _classify(raw):
    if not raw:
        return None, None
    q = raw.strip()
    q = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    try:
        ipaddress.ip_address(q)
        return q, 'ip'
    except ValueError:
        pass
    if HOSTNAME_RE.match(q.lower()):
        return q.lower(), 'domain'
    return None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _extract_records_buckets(payload):
    """Validin's DNS-history shape has gone through several revisions; tolerate
    both the top-level `records` map and the nested `data` variants."""
    if not isinstance(payload, dict):
        return None
    records = payload.get('records')
    if isinstance(records, dict):
        return records
    data = payload.get('data') or payload.get('result')
    if isinstance(data, dict):
        if isinstance(data.get('records'), dict):
            return data['records']
        # Direct map of type → list (older response shape).
        if data and all(isinstance(v, list) for v in data.values()):
            return data
    return None


def _format(target, target_kind, payload, max_per_type):
    buckets = _extract_records_buckets(payload)
    if not buckets:
        return None

    lines = [f"Validin DNS history for `{target}` ({target_kind}):"]
    rendered_any = False

    # Render the common record types in a stable order.
    type_order = ['A', 'AAAA', 'CNAME', 'NS', 'MX', 'TXT', 'SOA', 'PTR']
    seen_types = set()
    for rtype in type_order + sorted(buckets.keys()):
        if rtype in seen_types:
            continue
        seen_types.add(rtype)
        entries = buckets.get(rtype)
        if not isinstance(entries, list) or not entries:
            continue

        total = len(entries)
        truncated = total > max_per_type
        shown = entries[:max_per_type]

        lines.append('')
        # rtype is an external JSON dict key; wrap in inline-code so
        # the bold header can't render @-mentions or markdown links
        # if the upstream API returns an unexpected key shape.
        lines.append(f"**`{_cell(rtype)}` ({len(shown)} of {total}):**")
        lines.append('| Value | First seen | Last seen |')
        lines.append('| :- | :- | :- |')
        for r in shown:
            if not isinstance(r, dict):
                continue
            value = r.get('value') or r.get('rdata') or r.get('answer') or ''
            first = r.get('first_seen') or r.get('first_observed') or ''
            last = r.get('last_seen') or r.get('last_observed') or ''
            lines.append(f"| `{_cell(value)}` | `{_cell(first)}` | `{_cell(last)}` |")
        if truncated:
            lines.append(f"_…{total - max_per_type} more {rtype} record(s) not shown._")
        rendered_any = True

    if not rendered_any:
        return None
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    target, kind = _classify(params[0])
    if not target:
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('validin', {})
    token = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_per_type = int(getattr(settings, 'MAX_RECORDS_PER_TYPE', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not token or token.startswith('<'):
        return {'messages': [{'text': 'Validin is not configured. Set `key` in `settings.py` (https://app.validin.com/).'}]}

    # /axon/domains/dns/history/<d>  or  /axon/ips/dns/history/<ip>
    resource = 'domains' if kind == 'domain' else 'ips'
    url = base + f"{resource}/dns/history/" + requests.utils.quote(target, safe='')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Validin module',
    }

    try:
        resp = requests.get(url, headers=headers, allow_redirects=False, timeout=(10, 30))
    except requests.RequestException as e:
        log.exception("validin request failed")
        return {'messages': [{'text': f"Validin request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Validin: authentication failed — check the bearer token.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Validin: rate-limited (HTTP 429). Try again later.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"Validin: no DNS history for `{target}` ({kind})."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Validin returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("validin returned non-JSON")
        return {'messages': [{'text': 'Validin returned a non-JSON response.'}]}

    text = _format(target, kind, payload, max_per_type)
    if not text:
        return {'messages': [{'text': f"Validin: no DNS history records for `{target}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
