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
# Hunter.how query strings can contain spaces, equals, quotes, ANDs etc.
# Cap to 512 chars and reject control characters.
QUERY_RE = re.compile(r'^[^\x00-\x1f\x7f]{1,512}$')


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _build_query(raw):
    """Return (hunter_query_string, label) or (None, reason)."""
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
    # Pass through — assume the operator is using Hunter.how query syntax.
    return q, 'raw query (passed verbatim)'


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _format(label, payload, max_records):
    if not isinstance(payload, dict):
        return None

    code = payload.get('code')
    msg = payload.get('message') or ''
    if code and code != 200:
        return f"Hunter.how error (code {code}): `{_cell(msg or 'no detail')}`"

    data = payload.get('data') or {}
    if not isinstance(data, dict):
        return None
    items = data.get('list') or []
    total = data.get('total') if isinstance(data.get('total'), int) else len(items)

    lines = [f"Hunter.how — {label} — total {total}:"]
    if not items:
        lines.append('_No matching records._')
        return '\n'.join(lines)

    truncated = len(items) > max_records
    shown = items[:max_records]

    lines.append('')
    lines.append('| IP | Port | Domain | Country | AS | Title |')
    lines.append('| :- | :- | :- | :- | :- | :- |')
    for r in shown:
        if not isinstance(r, dict):
            continue
        lines.append('| `{ip}` | `{port}` | `{domain}` | `{country}` | `{asn}` | `{title}` |'.format(
            ip=_cell(r.get('ip') or '—'),
            port=_cell(r.get('port') or '—'),
            domain=_cell(_trim(r.get('domain') or '—', 40)),
            country=_cell(r.get('country') or '—'),
            asn=_cell(_trim(r.get('as_name') or r.get('asn') or '—', 30)),
            title=_cell(_trim(r.get('title') or '—', 50)),
        ))
    if truncated:
        lines.append(f"_…{len(items) - max_records} more record(s) on this page not shown._")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@hunterhow <IP|domain|hunter-query>`."}]}

    raw = ' '.join(params)
    hunter_q, label = _build_query(raw)
    if not hunter_q:
        return {'messages': [{'text': f"Hunter.how: {label}."}]}

    cfg = getattr(settings, 'APIURL', {}).get('hunterhow', {})
    key = cfg.get('key') or ''
    base = cfg.get('url') or 'https://api.hunter.how/search'
    max_records = int(getattr(settings, 'MAX_RECORDS', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'Hunter.how is not configured. Set `key` in `settings.py` (https://hunter.how/).'}]}

    # Query must be url-safe base64 (Hunter.how expects unpadded but accepts
    # both; we leave padding so the receiver doesn't have to guess).
    encoded = base64.urlsafe_b64encode(hunter_q.encode('utf-8')).decode('ascii')

    try:
        resp = requests.get(
            base,
            params={
                'api-key': key,
                'query': encoded,
                'page': 1,
                'page_size': max(max_records, 10),
            },
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot Hunter.how module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        # api-key lives in the query string; str(e) sometimes carries
        # the full URL — echo only the exception class.
        log.exception("hunter.how request failed")
        return {'messages': [{'text': f"Hunter.how request failed: `{type(e).__name__}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Hunter.how: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Hunter.how: rate-limited (HTTP 429). Free-tier daily quota may be exhausted.'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Hunter.how returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("hunter.how returned non-JSON")
        return {'messages': [{'text': 'Hunter.how returned a non-JSON response.'}]}

    text = _format(label, payload, max_records)
    if not text:
        return {'messages': [{'text': "Hunter.how: unrecognised response shape."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
