#!/usr/bin/env python3

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

# MAC accepted in colon, dash, or compact form. Output normalised to colon
# form (uppercase), which is what WiGLE prefers.
BSSID_RE = re.compile(r'^([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})$')
# SSIDs: 1-32 chars, printable. WiGLE accepts pretty much anything as a
# search term but we drop control chars + cap length to keep the request
# bounded.
SSID_RE = re.compile(r'^[^\x00-\x1f\x7f]{1,32}$')


def _normalize_bssid(raw):
    if not raw:
        return None
    m = BSSID_RE.match(raw.strip())
    if not m:
        return None
    return ':'.join(g.upper() for g in m.groups())


def _normalize_ssid(raw):
    if not raw:
        return None
    q = raw.strip()
    if not q:
        return None
    return q if SSID_RE.match(q) else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _format_search(query, payload, max_results):
    """Render /network/search response — list of matching access points."""
    if not isinstance(payload, dict):
        return None
    if not payload.get('success', True):
        msg = payload.get('message') or 'unknown error'
        return f"WiGLE search error: `{_cell(msg)}`"

    results = payload.get('results') or []
    total = payload.get('totalResults', len(results))
    if not isinstance(results, list) or not results:
        return f"WiGLE: no networks matched `{_cell(query)}`."

    truncated = len(results) > max_results
    shown = results[:max_results]

    lines = [f"WiGLE search for `{_cell(query)}` — total **{total}** match{'es' if total != 1 else ''}, showing {len(shown)}:"]
    lines.append('')
    lines.append('| BSSID | SSID | Enc | Ch | Lat,Lon | Last seen |')
    lines.append('| :- | :- | :- | :- | :- | :- |')
    for r in shown:
        if not isinstance(r, dict):
            continue
        netid = r.get('netid') or '?'
        ssid = r.get('ssid') or ''
        enc = r.get('encryption') or '?'
        ch = r.get('channel') or '?'
        lat = r.get('trilat')
        lon = r.get('trilong')
        loc = f"{lat:.4f},{lon:.4f}" if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) else '?'
        last = r.get('lasttime') or r.get('lastupdt') or '?'
        lines.append(f"| `{_cell(netid)}` | `{_cell(_trim(ssid, 30))}` | `{_cell(enc)}` | `{_cell(ch)}` | `{_cell(loc)}` | `{_cell(last)}` |")

    if truncated:
        lines.append(f"_…{total - max_results} more match(es) not shown — narrow your search to see them._")
    return '\n'.join(lines)


def _format_detail(bssid, payload):
    """Render /network/detail response — single AP detail."""
    if not isinstance(payload, dict):
        return None
    if not payload.get('success', True):
        msg = payload.get('message') or 'unknown error'
        return f"WiGLE detail error: `{_cell(msg)}`"

    results = payload.get('results') or []
    if not results:
        return f"WiGLE: no record for `{bssid}`."
    rec = results[0] if isinstance(results, list) else results
    if not isinstance(rec, dict):
        return None

    rows = [('BSSID', bssid)]
    for k_in, k_out in [
        ('ssid', 'SSID'),
        ('encryption', 'Encryption'),
        ('channel', 'Channel'),
        ('type', 'Type'),
        ('country', 'Country'),
        ('region', 'Region'),
        ('city', 'City'),
        ('firsttime', 'First seen'),
        ('lasttime', 'Last seen'),
        ('trilat', 'Latitude'),
        ('trilong', 'Longitude'),
    ]:
        v = rec.get(k_in)
        if v not in (None, ''):
            rows.append((k_out, v))

    lines = [f"WiGLE record for `{bssid}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")
    lat = rec.get('trilat')
    lon = rec.get('trilong')
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        lines.append(f"| Map | [OpenStreetMap](https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}) |")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@wigle [ssid|bssid] <value>`."}]}

    # Subcommand vs. auto-route. If first arg matches a subcommand, take the
    # rest as the value; else treat the whole thing as an indicator and
    # auto-route by shape.
    sub = None
    raw_value = None
    if params[0].lower() in ('ssid', 'bssid') and len(params) >= 2:
        sub = params[0].lower()
        raw_value = ' '.join(params[1:])
    else:
        raw_value = ' '.join(params)
        # Auto-route — MAC-shape => bssid, else ssid.
        if _normalize_bssid(raw_value):
            sub = 'bssid'
        else:
            sub = 'ssid'

    if sub == 'bssid':
        normalized = _normalize_bssid(raw_value)
    else:
        normalized = _normalize_ssid(raw_value)

    if not normalized:
        return {'messages': [{'text': f"wigle {sub}: `{_cell(raw_value)}` is not a valid {sub.upper()}."}]}

    cfg = getattr(settings, 'APIURL', {}).get('wigle', {})
    api_name = cfg.get('name') or ''
    api_token = cfg.get('token') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_results = int(getattr(settings, 'MAX_RESULTS', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not api_name or not api_token or api_name.startswith('<') or api_token.startswith('<'):
        return {'messages': [{'text': 'WiGLE is not configured. Set `name` and `token` in `settings.py` (https://wigle.net/).'}]}

    headers = {
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot WiGLE module',
    }
    auth = HTTPBasicAuth(api_name, api_token)

    if sub == 'bssid':
        url = base + 'network/detail'
        params_q = {'netid': normalized}
    else:
        url = base + 'network/search'
        # `ssidlike` does substring match; `ssid` requires exact match.
        # Substring is what operators usually want.
        params_q = {'ssidlike': normalized, 'first': 0, 'resultsPerPage': max(max_results, 10)}

    try:
        resp = requests.get(
            url,
            params=params_q,
            headers=headers,
            auth=auth,
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("wigle request failed")
        return {'messages': [{'text': f"WiGLE request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'WiGLE: authentication failed — check `name` / `token`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'WiGLE: rate-limited (HTTP 429). Daily query budget may be exhausted.'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"WiGLE returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("wigle returned non-JSON")
        return {'messages': [{'text': 'WiGLE returned a non-JSON response.'}]}

    if sub == 'bssid':
        text = _format_detail(normalized, payload)
    else:
        text = _format_search(normalized, payload, max_results)

    if not text:
        return {'messages': [{'text': f"WiGLE: unrecognised response shape for `{normalized}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
