#!/usr/bin/env python3

import base64
import ipaddress
import json
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
# Cap raw queries at 512 chars; reject control chars.
QUERY_RE = re.compile(r'^[^\x00-\x1f\x7f]{1,512}$')


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _build_query(raw):
    """Return (zoomeye_query_string, label) or (None, reason)."""
    if not raw:
        return None, 'empty input'
    q = raw.strip()
    if not q:
        return None, 'empty input'
    if not QUERY_RE.match(q):
        return None, 'query rejected (control chars or >512 chars)'

    bare = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    bare = re.sub(r'^(?:https?|hxxps?)://', '', bare)
    bare_first = bare.split('/', 1)[0]
    if _is_ip(bare_first):
        return f'ip="{bare_first}"', f'IP query (auto-wrapped from `{bare_first}`)'
    if HOSTNAME_RE.match(bare_first.lower()):
        return f'hostname="{bare_first.lower()}"', f'hostname query (auto-wrapped from `{bare_first.lower()}`)'
    return q, 'raw query (passed verbatim)'


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _extract_field(record, *paths):
    """Walk dotted paths through a nested record. Returns first hit or None."""
    for path in paths:
        cur = record
        ok = True
        for part in path.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None and cur != '':
            return cur
    return None


def _format(label, payload, max_records):
    if not isinstance(payload, dict):
        return None
    code = payload.get('code')
    msg = payload.get('message') or payload.get('error') or ''
    if code is not None and code != 0 and code != 60000:
        return f"Zoomeye error (code {code}): `{_cell(msg or 'no detail')}`"

    data = payload.get('data') or payload.get('matches') or []
    if not isinstance(data, list):
        return None
    total = payload.get('total', len(data))

    lines = [f"Zoomeye — {label} — total {total}:"]
    if not data:
        lines.append('_No matching records._')
        return '\n'.join(lines)

    truncated = len(data) > max_records
    shown = data[:max_records]

    lines.append('')
    lines.append('| IP | Port | Service | Country | Banner |')
    lines.append('| :- | :- | :- | :- | :- |')
    for r in shown:
        if not isinstance(r, dict):
            continue
        ip = _extract_field(r, 'ip', 'host.ip', 'portinfo.ip')
        port = _extract_field(r, 'port', 'portinfo.port')
        service = _extract_field(r, 'service', 'portinfo.service', 'portinfo.product')
        country = _extract_field(r, 'geoinfo.country.names.en',
                                 'geoinfo.country.name', 'geoinfo.country', 'country')
        banner = _extract_field(r, 'banner', 'portinfo.banner', 'portinfo.data')
        if isinstance(country, dict):
            country = country.get('en') or country.get('name')
        lines.append('| `{ip}` | `{port}` | `{service}` | `{country}` | `{banner}` |'.format(
            ip=_cell(ip or '—'),
            port=_cell(port or '—'),
            service=_cell(_trim(service or '—', 30)),
            country=_cell(country or '—'),
            banner=_cell(_trim(banner or '—', 80)),
        ))
    if truncated:
        lines.append(f"_…{len(data) - max_records} more record(s) not shown._")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@zoomeye <IP|domain|query>`."}]}

    raw = ' '.join(params)
    z_query, label = _build_query(raw)
    if not z_query:
        return {'messages': [{'text': f"Zoomeye: {label}."}]}

    cfg = getattr(settings, 'APIURL', {}).get('zoomeye', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_records = int(getattr(settings, 'MAX_RECORDS', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'Zoomeye is not configured. Set `key` in `settings.py` (https://www.zoomeye.ai/).'}]}

    # Zoomeye v2 search endpoint expects a base64-encoded query in JSON POST.
    encoded = base64.b64encode(z_query.encode('utf-8')).decode('ascii')
    url = base + 'search'
    headers = {
        'API-KEY': key,
        'Content-Type': settings.CONTENTTYPE,
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Zoomeye module',
    }
    body = {'qbase64': encoded, 'page': 1, 'pagesize': max(max_records, 10)}

    try:
        resp = requests.post(
            url,
            data=json.dumps(body),
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("zoomeye request failed")
        return {'messages': [{'text': f"Zoomeye request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Zoomeye: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Zoomeye: rate-limited (HTTP 429). Free-tier daily quota may be exhausted.'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Zoomeye returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("zoomeye returned non-JSON")
        return {'messages': [{'text': 'Zoomeye returned a non-JSON response.'}]}

    text = _format(label, payload, max_records)
    if not text:
        return {'messages': [{'text': "Zoomeye: unrecognised response shape."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
