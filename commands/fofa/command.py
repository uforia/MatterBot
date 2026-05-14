#!/usr/bin/env python3

import base64
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
QUERY_RE = re.compile(r'^[^\x00-\x1f\x7f]{1,512}$')


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _build_query(raw):
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
        return f'domain="{bare_first.lower()}"', f'domain query (auto-wrapped from `{bare_first.lower()}`)'
    return q, 'raw query (passed verbatim)'


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _format(label, fields, payload, max_records):
    if not isinstance(payload, dict):
        return None

    # Fofa surfaces failure both via HTTP 200 + {error: true} and via the
    # error flag being a non-bool truthy value. Handle both.
    if payload.get('error'):
        msg = payload.get('errmsg') or 'unknown error'
        return f"Fofa error: `{_cell(msg)}`"

    results = payload.get('results') or []
    total = payload.get('size') if isinstance(payload.get('size'), int) else len(results)

    lines = [f"Fofa — {label} — total {total}:"]
    if not results:
        lines.append('_No matching records._')
        return '\n'.join(lines)

    truncated = len(results) > max_records
    shown = results[:max_records]

    # The fields argument is comma-separated; Fofa returns each row as a
    # parallel list with values in field-declaration order.
    field_list = [f.strip() for f in fields.split(',') if f.strip()]

    lines.append('')
    lines.append('| ' + ' | '.join(field_list) + ' |')
    lines.append('| ' + ' | '.join([':-'] * len(field_list)) + ' |')

    # Per-field truncation widths so a long server-banner string can't
    # blow out the table. Width depends on field type.
    widths = {
        'host':            60,
        'ip':              40,
        'port':            10,
        'protocol':        12,
        'country_name':    20,
        'as_organization': 30,
        'server':          40,
        'title':           50,
    }

    for row in shown:
        if not isinstance(row, list):
            continue
        cells = []
        for i, fname in enumerate(field_list):
            v = row[i] if i < len(row) else ''
            cells.append('`' + _cell(_trim(v or '—', widths.get(fname, 40))) + '`')
        lines.append('| ' + ' | '.join(cells) + ' |')

    if truncated:
        lines.append(f"_…{len(results) - max_records} more record(s) on this page not shown._")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@fofa <IP|domain|query>`."}]}

    raw = ' '.join(params)
    f_query, label = _build_query(raw)
    if not f_query:
        return {'messages': [{'text': f"Fofa: {label}."}]}

    cfg = getattr(settings, 'APIURL', {}).get('fofa', {})
    email = cfg.get('email') or ''
    key = cfg.get('key') or ''
    base = cfg.get('url') or 'https://fofa.info/api/v1/search/all'
    fields = getattr(settings, 'FOFA_FIELDS', 'host,ip,port,protocol,country_name,as_organization,server,title')
    max_records = int(getattr(settings, 'MAX_RECORDS', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not email or not key or email.startswith('<') or key.startswith('<'):
        return {'messages': [{'text': 'Fofa is not configured. Set `email` and `key` in `settings.py` (free tier at https://en.fofa.info/).'}]}

    encoded = base64.b64encode(f_query.encode('utf-8')).decode('ascii')

    try:
        resp = requests.get(
            base,
            params={
                'email': email,
                'key': key,
                'qbase64': encoded,
                'size': max(max_records, 10),
                'fields': fields,
            },
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot Fofa module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        # email + key in the query string; do not echo the URL.
        log.exception("fofa request failed")
        return {'messages': [{'text': f"Fofa request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Fofa: authentication failed — check `email` / `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Fofa: rate-limited (HTTP 429).'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Fofa returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("fofa returned non-JSON")
        return {'messages': [{'text': 'Fofa returned a non-JSON response.'}]}

    text = _format(label, fields, payload, max_records)
    if not text:
        return {'messages': [{'text': "Fofa: unrecognised response shape."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
