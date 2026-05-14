#!/usr/bin/env python3

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

# 32-bit ASN range is 0..4294967295. PeeringDB rejects out-of-range queries
# server-side too, but rejecting locally avoids the round-trip.
ASN_RE = re.compile(r'^(?:AS)?([0-9]{1,10})$', re.IGNORECASE)


def _normalize_asn(raw):
    if not raw:
        return None
    m = ASN_RE.match(raw.strip())
    if not m:
        return None
    n = int(m.group(1))
    if n < 0 or n > 4294967295:
        return None
    return n


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _fetch(session, url, params, headers, timeout):
    try:
        resp = session.get(url, params=params, headers=headers, allow_redirects=False, timeout=timeout)
    except requests.RequestException as e:
        log.exception("peeringdb request failed (%s)", url)
        return None, f"PeeringDB request failed: `{e}`"
    if resp.status_code == 401 or resp.status_code == 403:
        return None, 'PeeringDB: authentication failed — clear the `key` setting or supply a valid one.'
    if resp.status_code == 404:
        return None, None  # treated as "no record"
    if resp.status_code == 429:
        return None, 'PeeringDB: rate-limited (HTTP 429). Try again later or configure an API key.'
    if resp.status_code != 200:
        return None, f"PeeringDB returned HTTP {resp.status_code} for `{url.rsplit('/', 1)[-1]}`."
    try:
        return resp.json(), None
    except ValueError:
        log.exception("peeringdb returned non-JSON")
        return None, 'PeeringDB returned a non-JSON response.'


def _format(asn, net_record, ix_records, fac_records, max_ix, max_fac):
    rows = [
        ('ASN', f"AS{asn}"),
    ]
    name = net_record.get('name')
    if name:
        rows.append(('Network', name))
    aka = net_record.get('aka')
    if aka and aka != name:
        rows.append(('Also known as', aka))
    org = (net_record.get('org') or {}).get('name') if isinstance(net_record.get('org'), dict) else None
    org = org or net_record.get('org_name')
    if org:
        rows.append(('Organisation', org))
    net_type = net_record.get('info_type')
    if net_type:
        rows.append(('Network type', net_type))
    traffic = net_record.get('info_traffic')
    if traffic:
        rows.append(('Traffic estimate', traffic))
    scope = net_record.get('info_scope')
    if scope:
        rows.append(('Scope', scope))
    ratio = net_record.get('info_ratio')
    if ratio:
        rows.append(('Traffic ratio', ratio))
    irr = net_record.get('irr_as_set')
    if irr:
        rows.append(('IRR AS-set', irr))
    policy = net_record.get('policy_general')
    if policy:
        rows.append(('Peering policy', policy))
    website = net_record.get('website')
    if website:
        rows.append(('Website', website))

    lines = [f"PeeringDB record for `AS{asn}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # IXPs the network is present at.
    if ix_records:
        lines.append('')
        total = len(ix_records)
        truncated = total > max_ix
        shown = ix_records[:max_ix]
        lines.append(f"**Internet exchanges ({len(shown)} of {total}):**")
        for r in shown:
            if not isinstance(r, dict):
                continue
            ix_name = r.get('name') or r.get('ix_name') or '?'
            speed = r.get('speed')
            ipv4 = r.get('ipaddr4')
            ipv6 = r.get('ipaddr6')
            ips = ' / '.join(filter(None, [ipv4, ipv6]))
            speed_label = f"{speed/1000:g} Gbps" if isinstance(speed, (int, float)) and speed else '?'
            extra = ips or '—'
            lines.append(f"- `{_cell(ix_name)}` · {speed_label} · {_cell(extra)}")
        if truncated:
            lines.append(f"_…{total - max_ix} more not shown._")

    # Facilities (data centres / carrier hotels).
    if fac_records:
        lines.append('')
        total = len(fac_records)
        truncated = total > max_fac
        shown = fac_records[:max_fac]
        lines.append(f"**Facilities ({len(shown)} of {total}):**")
        for r in shown:
            if not isinstance(r, dict):
                continue
            fac_name = r.get('name') or '?'
            city = r.get('city')
            country = r.get('country')
            loc_bits = ', '.join(filter(None, [city, country]))
            lines.append(f"- `{_cell(fac_name)}`" + (f" — {_cell(loc_bits)}" if loc_bits else ''))
        if truncated:
            lines.append(f"_…{total - max_fac} more not shown._")

    lines.append('')
    lines.append(f"Reference: [PeeringDB AS{asn}](https://www.peeringdb.com/asn/{asn})")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    asn = _normalize_asn(params[0])
    if asn is None:
        # Silent no-op on shape mismatch (matches the rest of the TI modules).
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('peeringdb', {})
    base = (cfg.get('url') or '').rstrip('/') + '/'
    key = cfg.get('key') or ''
    max_ix = int(getattr(settings, 'MAX_IX', 10))
    max_fac = int(getattr(settings, 'MAX_FAC', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    headers = {
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot PeeringDB module',
    }
    if key and not key.startswith('<'):
        headers['Authorization'] = f'Api-Key {key}'

    session = requests.Session()
    timeout = (10, 30)

    # 1. Network record by ASN.
    net_payload, err = _fetch(session, base + 'net', {'asn': asn}, headers, timeout)
    if err:
        return {'messages': [{'text': err}]}
    if not net_payload or not isinstance(net_payload.get('data'), list) or not net_payload['data']:
        return {'messages': [{'text': f"PeeringDB: no network record for `AS{asn}`."}]}
    net_record = net_payload['data'][0]
    net_id = net_record.get('id')

    # 2. IXP presence (netixlan) — links the network to internet exchanges.
    ix_records = []
    if net_id:
        ixlan_payload, err = _fetch(session, base + 'netixlan', {'net_id': net_id}, headers, timeout)
        if ixlan_payload and isinstance(ixlan_payload.get('data'), list):
            ix_records = ixlan_payload['data']

    # 3. Facilities (netfac).
    fac_records = []
    if net_id:
        netfac_payload, err = _fetch(session, base + 'netfac', {'net_id': net_id}, headers, timeout)
        if netfac_payload and isinstance(netfac_payload.get('data'), list):
            fac_records = netfac_payload['data']

    text = _format(asn, net_record, ix_records, fac_records, max_ix, max_fac)
    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
