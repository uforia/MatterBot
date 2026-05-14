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
    """Return (normalized_value, indicator_type) or (None, None).

    Indicator types follow PulseDive's vocabulary: 'ip', 'ipv6', 'domain',
    'url', 'sha256', 'sha1', 'md5'.
    """
    if not raw:
        return None, None
    q = raw.strip()
    # Hash check uses the raw token (case-insensitive).
    if SHA256_RE.match(q):
        return q.lower(), 'sha256'
    if SHA1_RE.match(q):
        return q.lower(), 'sha1'
    if MD5_RE.match(q):
        return q.lower(), 'md5'
    # URL — keep scheme intact for PulseDive; restore hxxp defang.
    norm = q.lower().replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    if re.match(r'^hxxps?://', norm):
        norm = norm.replace('hxxps://', 'https://', 1).replace('hxxp://', 'http://', 1)
    if norm.startswith(('http://', 'https://')):
        return norm, 'url'
    # IP / domain.
    if _is_ip(norm):
        try:
            return norm, 'ipv6' if isinstance(ipaddress.ip_address(norm), ipaddress.IPv6Address) else 'ip'
        except ValueError:
            return None, None
    if HOSTNAME_RE.match(norm):
        return norm, 'domain'
    return None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format(indicator, indicator_type, payload, max_threats, max_feeds):
    if not isinstance(payload, dict):
        return None

    # "Not found" detection — PulseDive returns an `error` field when the
    # indicator hasn't been observed.
    err = payload.get('error')
    if err and not payload.get('iid'):
        return f"PulseDive: `{indicator}` not found in the dataset (`{_cell(err)}`)."

    rows = []
    rows.append(('Indicator', indicator))
    detected_type = payload.get('type')
    if detected_type and detected_type != indicator_type:
        rows.append(('Type', f"{detected_type} (queried as {indicator_type})"))
    else:
        rows.append(('Type', detected_type or indicator_type))
    risk = payload.get('risk_recommended') or payload.get('risk')
    if risk:
        rows.append(('Risk', risk))
    first = payload.get('stamp_seen') or payload.get('stamp_added')
    if first:
        rows.append(('First seen', first))
    updated = payload.get('stamp_updated')
    if updated:
        rows.append(('Last updated', updated))
    manualrisk = payload.get('manualrisk') or payload.get('risk_manual')
    if manualrisk:
        rows.append(('Manual risk', manualrisk))

    lines = [f"PulseDive lookup for `{indicator}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    iid = payload.get('iid')
    if iid:
        lines.append(f"| Reference | [PulseDive indicator {iid}](https://pulsedive.com/indicator/?iid={iid}) |")

    threats = payload.get('threats') or []
    if isinstance(threats, list) and threats:
        total = len(threats)
        truncated = total > max_threats
        shown = threats[:max_threats]
        lines.append('')
        lines.append(f"**Threats ({len(shown)} of {total}):**")
        for t in shown:
            if not isinstance(t, dict):
                continue
            name = t.get('name') or '?'
            cat = t.get('category') or ''
            risk = t.get('risk') or ''
            extra = ' · '.join(filter(None, [cat, risk]))
            lines.append(f"- `{_cell(name)}`" + (f" — {_cell(extra)}" if extra else ''))
        if truncated:
            lines.append(f"_…{total - max_threats} more threat(s) not shown._")

    feeds = payload.get('feeds') or []
    if isinstance(feeds, list) and feeds:
        total = len(feeds)
        truncated = total > max_feeds
        shown = feeds[:max_feeds]
        lines.append('')
        lines.append(f"**Feeds ({len(shown)} of {total}):**")
        for f in shown:
            if not isinstance(f, dict):
                continue
            name = f.get('name') or '?'
            org = f.get('organization') or f.get('org') or ''
            extra = org
            lines.append(f"- `{_cell(name)}`" + (f" — {_cell(extra)}" if extra else ''))
        if truncated:
            lines.append(f"_…{total - max_feeds} more feed(s) not shown._")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    indicator, indicator_type = _classify(raw)
    if not indicator:
        # Silent no-op on shape mismatch (matches the rest of the TI modules).
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('pulsedive', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_threats = int(getattr(settings, 'MAX_THREATS', 12))
    max_feeds = int(getattr(settings, 'MAX_FEEDS', 12))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'PulseDive is not configured. Set `key` in `settings.py` (https://pulsedive.com/).'}]}

    # /info.php is the read endpoint that doesn't queue a new scan.
    url = base + 'info.php'
    try:
        resp = requests.get(
            url,
            params={'indicator': indicator, 'pretty': '1', 'key': key},
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot PulseDive module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        # Note: the apikey is in the query string. Don't echo the URL.
        log.exception("pulsedive request failed")
        return {'messages': [{'text': f"PulseDive request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'PulseDive: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'PulseDive: rate-limited (HTTP 429). Free tier limits apply.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"PulseDive: no record for `{indicator}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"PulseDive returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("pulsedive returned non-JSON")
        return {'messages': [{'text': 'PulseDive returned a non-JSON response.'}]}

    text = _format(indicator, indicator_type, payload, max_threats, max_feeds)
    if not text:
        return {'messages': [{'text': f"PulseDive: unrecognised response shape for `{indicator}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
