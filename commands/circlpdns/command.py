#!/usr/bin/env python3

import datetime
import ipaddress
import json
import re
import requests
from requests.auth import HTTPBasicAuth

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

# RFC-1123 hostname. Up to 253 chars total, 2-63 char TLD.
HOSTNAME_RE = re.compile(
    r'^(?=.{1,253}$)'
    r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)\.)+'
    r'[a-zA-Z]{2,63}$'
)


def _is_ip_or_net(value):
    try:
        ipaddress.ip_network(value, strict=False)
        return True
    except ValueError:
        return False


def _validate_query(raw):
    """Normalize and classify the operator input. Returns (normalized, kind) or (None, reason)."""
    if not raw:
        return None, 'empty input'
    q = raw.strip().lower()
    # Restore common defang forms before checking.
    q = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    # Check IP/CIDR first — must happen before any path-stripping because CIDR uses '/'.
    if _is_ip_or_net(q):
        return q, 'IP/CIDR'
    # Strip URL path (anything after the host) before the hostname check.
    q = q.split('/', 1)[0]
    if HOSTNAME_RE.match(q):
        return q, 'domain'
    return None, 'must be a domain, IPv4/IPv6 address, or CIDR (rejected)'


def _fmt_ts(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError, OverflowError):
        return '?'


def _cell(value):
    """Escape pipe and backtick so the markdown table stays well-formed."""
    return str(value).replace('`', '').replace('|', '/')


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    query, kind = _validate_query(raw)
    if not query:
        # Silent no-op on shape mismatch — matches the urlhaus / malwarebazaar /
        # threatfox convention so an `@ioc <hash>` fan-out doesn't spam the
        # channel with rejection notices from every TI module.
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('circlpdns', {})
    user = cfg.get('user') or ''
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_rows = int(getattr(settings, 'MAX_ROWS', 50))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not user or not key or user.startswith('<') or key.startswith('<'):
        return {'messages': [{'text': 'CIRCL Passive DNS is not configured. Set `user` and `key` in `settings.py` (https://www.circl.lu/services/passive-dns/).'}]}

    url = base + requests.utils.quote(query, safe='')
    try:
        resp = requests.get(
            url,
            auth=HTTPBasicAuth(user, key),
            headers={
                'User-Agent': 'MatterBot CIRCL pDNS module',
                'Accept': 'application/x-ndjson, application/json',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("circlpdns request failed")
        return {'messages': [{'text': f"CIRCL Passive DNS request failed: `{e}`"}]}

    if resp.status_code == 401:
        return {'messages': [{'text': 'CIRCL Passive DNS: authentication failed — check `user`/`key`.'}]}
    if resp.status_code == 403:
        return {'messages': [{'text': 'CIRCL Passive DNS: forbidden (account not authorised for this query type?).'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"CIRCL Passive DNS: no records for `{query}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"CIRCL Passive DNS returned HTTP {resp.status_code}."}]}

    rows = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(rec)

    if not rows:
        return {'messages': [{'text': f"CIRCL Passive DNS: no records for `{query}`."}]}

    def _t(rec):
        v = rec.get('time_last') or rec.get('time_first') or 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    rows.sort(key=_t, reverse=True)
    total = len(rows)
    truncated = total > max_rows
    rows = rows[:max_rows]

    out = [f"CIRCL Passive DNS for `{query}` ({kind}) — showing {len(rows)} of {total} record{'s' if total != 1 else ''}:"]
    out.append('| First seen | Last seen | rrtype | rrname | rdata |')
    out.append('| :- | :- | :- | :- | :- |')
    for rec in rows:
        out.append('| `{f}` | `{l}` | `{rrt}` | `{rrn}` | `{rd}` |'.format(
            f=_fmt_ts(rec.get('time_first')),
            l=_fmt_ts(rec.get('time_last')),
            rrt=_cell(rec.get('rrtype', '?')),
            rrn=_cell(rec.get('rrname', '')),
            rd=_cell(rec.get('rdata', '')),
        ))
    if truncated:
        out.append(f"_…truncated; {total - max_rows} more record(s) not shown._")

    text = '\n'.join(out)
    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'
    messages.append({'text': text})
    return {'messages': messages}
