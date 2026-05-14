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

# IP-only validator — HoneyDB endpoints accept IPv4/IPv6 addresses, no CIDR.
def _normalize_ip(raw):
    if not raw:
        return None
    q = raw.strip().lower()
    q = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    try:
        return str(ipaddress.ip_address(q))
    except ValueError:
        return None


def _cell(value):
    """Escape pipe and backtick so the markdown table stays well-formed."""
    return str(value).replace('`', '').replace('|', '/')


def _format_threat_info(ip, data):
    """Render the /threat-info/{ip} response.

    HoneyDB returns either a JSON object or a single-element list of objects
    depending on the deployment — handle both.
    """
    if isinstance(data, list):
        if not data:
            return None
        data = data[0]
    if not isinstance(data, dict):
        return None

    count = data.get('count', '?')
    last_seen = data.get('last_seen', '?')
    ports = data.get('ports') or []
    services = data.get('services') or []

    lines = [f"HoneyDB threat-info for `{ip}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    lines.append(f"| **Hits** | `{_cell(count)}` |")
    lines.append(f"| **Last seen** | `{_cell(last_seen)}` |")
    if ports:
        ports_str = ', '.join(str(p) for p in ports[:50])
        if len(ports) > 50:
            ports_str += f", …(+{len(ports) - 50})"
        lines.append(f"| **Ports** | `{_cell(ports_str)}` |")
    if services:
        svc_str = ', '.join(str(s) for s in services[:50])
        if len(services) > 50:
            svc_str += f", …(+{len(services) - 50})"
        lines.append(f"| **Services** | `{_cell(svc_str)}` |")
    lines.append(f"| Reference | [HoneyDB IP report](https://honeydb.io/explore/{ip}) |")
    return '\n'.join(lines)


def _format_history(ip, data, max_rows):
    """Render the /ip-history/{ip} response (list of per-day records)."""
    if not isinstance(data, list) or not data:
        return None
    total = len(data)
    truncated = total > max_rows
    rows = data[:max_rows]

    lines = [f"HoneyDB IP history for `{ip}` — showing {len(rows)} of {total} record{'s' if total != 1 else ''}:"]
    lines.append('| Date | Count | Ports | Services |')
    lines.append('| :- | :- | :- | :- |')
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        date = _cell(rec.get('date', '?'))
        count = _cell(rec.get('count', '?'))
        ports = rec.get('ports') or []
        services = rec.get('services') or []
        ports_str = ', '.join(str(p) for p in ports[:20]) or '—'
        svc_str = ', '.join(str(s) for s in services[:20]) or '—'
        lines.append(f"| `{date}` | `{count}` | `{_cell(ports_str)}` | `{_cell(svc_str)}` |")
    if truncated:
        lines.append(f"_…truncated; {total - max_rows} earlier day(s) not shown._")
    lines.append(f"Reference: [HoneyDB IP report](https://honeydb.io/explore/{ip})")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    # Subcommand parsing: `<ip>` or `history <ip>` or `<ip> history`.
    args = [p for p in params if p]
    mode = 'threat-info'
    if args and args[0].lower() in ('history', 'hist', 'iphistory'):
        mode = 'history'
        args = args[1:]
    elif len(args) >= 2 and args[1].lower() in ('history', 'hist'):
        mode = 'history'
        args = [args[0]]

    if not args:
        return {'messages': messages}

    ip = _normalize_ip(args[0])
    if not ip:
        # Silent no-op on shape mismatch — convention shared with the rest of
        # the TI modules so `@ioc <hash>` doesn't spam rejections.
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('honeydb', {})
    api_id = cfg.get('id') or ''
    api_key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_history = int(getattr(settings, 'MAX_HISTORY_ROWS', 30))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not api_id or not api_key or api_id.startswith('<') or api_key.startswith('<'):
        return {'messages': [{'text': 'HoneyDB is not configured. Set `id` and `key` in `settings.py` (free at https://honeydb.io/).'}]}

    endpoint = 'ip-history' if mode == 'history' else 'threat-info'
    url = base + endpoint + '/' + requests.utils.quote(ip, safe='')

    headers = {
        'X-HoneyDb-ApiId': api_id,
        'X-HoneyDb-ApiKey': api_key,
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot HoneyDB module',
    }

    try:
        resp = requests.get(
            url,
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("honeydb request failed")
        return {'messages': [{'text': f"HoneyDB request failed: `{e}`"}]}

    if resp.status_code == 401:
        return {'messages': [{'text': 'HoneyDB: authentication failed — check `id`/`key`.'}]}
    if resp.status_code == 403:
        return {'messages': [{'text': 'HoneyDB: forbidden (rate-limited, or account not authorised for this query?).'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"HoneyDB: no `{mode}` records for `{ip}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"HoneyDB returned HTTP {resp.status_code} for `{mode}`."}]}

    try:
        data = resp.json()
    except ValueError:
        log.exception("honeydb response was not valid JSON")
        return {'messages': [{'text': 'HoneyDB returned a non-JSON response.'}]}

    if mode == 'history':
        text = _format_history(ip, data, max_history)
    else:
        text = _format_threat_info(ip, data)

    if not text:
        return {'messages': [{'text': f"HoneyDB: no `{mode}` records for `{ip}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
