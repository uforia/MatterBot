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


def _normalize_ip_or_domain(raw):
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


def _extract_data(payload):
    """Netlas wraps the host record in different shapes depending on endpoint
    and version. Try the documented variants in order."""
    if not isinstance(payload, dict):
        return None
    items = payload.get('items')
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            return first.get('data') or first.get('_source') or first
    if isinstance(payload.get('data'), dict):
        return payload['data']
    if 'ip' in payload or 'domain' in payload:
        return payload
    return None


def _format_host(target, target_kind, data, max_ports, max_domains):
    rows = []
    rows.append(('Target', f"{target} ({target_kind})"))

    ip = data.get('ip')
    if ip and ip != target:
        rows.append(('IP', ip))
    asn = data.get('asn') or data.get('as') or {}
    if isinstance(asn, dict):
        number = asn.get('number') or asn.get('asn')
        org = asn.get('organization') or asn.get('org')
        if number:
            rows.append(('ASN', number))
        if org:
            rows.append(('AS organisation', org))
    elif asn:
        rows.append(('ASN', asn))
    geo = data.get('geo') or {}
    if isinstance(geo, dict):
        country = geo.get('country')
        city = geo.get('city')
        if country:
            rows.append(('Country', country + (f" / {city}" if city else '')))
    domains = data.get('domain') or data.get('domains') or []
    if isinstance(domains, str):
        domains = [domains]
    if domains:
        capped = domains[:max_domains]
        d_str = ', '.join(_cell(d) for d in capped)
        if len(domains) > max_domains:
            d_str += f", …(+{len(domains) - max_domains})"
        rows.append(('Domains', d_str))

    lines = [f"Netlas host record for `{target}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # Ports + services
    ports = data.get('ports') or []
    if isinstance(ports, list) and ports:
        total = len(ports)
        truncated = total > max_ports
        shown = ports[:max_ports]
        lines.append('')
        lines.append(f"**Ports / services ({len(shown)} of {total}):**")
        lines.append('| Port | Protocol | Service | Banner |')
        lines.append('| :- | :- | :- | :- |')
        for p in shown:
            if isinstance(p, dict):
                port = p.get('port', '?')
                proto = p.get('protocol', '?')
                service = p.get('service') or p.get('product') or ''
                banner = p.get('banner') or p.get('data') or ''
                if isinstance(banner, str) and len(banner) > 80:
                    banner = banner[:79].rstrip() + '…'
                lines.append(f"| `{_cell(port)}` | `{_cell(proto)}` | `{_cell(service)}` | `{_cell(banner)}` |")
            else:
                # Plain int — older API responses just list port numbers.
                lines.append(f"| `{_cell(p)}` | — | — | — |")
        if truncated:
            lines.append(f"_…{total - max_ports} more port(s) not shown._")

    return '\n'.join(lines)


def _format_whois(target, target_kind, data):
    rows = [('Target', f"{target} ({target_kind})")]
    if target_kind == 'ip':
        for k_in, k_out in [
            ('asn', 'ASN'),
            ('country', 'Country'),
            ('organization', 'Organisation'),
            ('net_name', 'Network name'),
            ('cidr', 'CIDR'),
            ('range', 'Range'),
            ('description', 'Description'),
        ]:
            v = data.get(k_in)
            if v:
                rows.append((k_out, v))
    else:
        for k_in, k_out in [
            ('registrar', 'Registrar'),
            ('creation_date', 'Created'),
            ('updated_date', 'Updated'),
            ('expiration_date', 'Expires'),
            ('name_servers', 'Name servers'),
            ('status', 'Status'),
            ('emails', 'Emails'),
        ]:
            v = data.get(k_in)
            if v:
                if isinstance(v, list):
                    v = ', '.join(str(x) for x in v[:8])
                rows.append((k_out, v))

    lines = [f"Netlas WHOIS for `{target}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{
            'text': "Usage: `@netlas [host|whois] <IP|domain>` — bare `@netlas <ip|host>` defaults to `host`."
        }]}

    # Subcommand vs. bare-target. host is default; whois explicit.
    sub = 'host'
    target = params[0]
    if params[0].lower() in ('host', 'whois') and len(params) >= 2:
        sub = params[0].lower()
        target = params[1]

    normalized, kind = _normalize_ip_or_domain(target)
    if not normalized:
        if params[0].lower() in ('host', 'whois'):
            return {'messages': [{'text': f"netlas {sub}: `{_cell(target)}` is not a valid IP or domain."}]}
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('netlas', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_ports = int(getattr(settings, 'MAX_PORTS', 20))
    max_domains = int(getattr(settings, 'MAX_DOMAINS', 15))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'Netlas is not configured. Set `key` in `settings.py` (free tier at https://netlas.io/).'}]}

    if sub == 'whois':
        endpoint = 'whois_ip/' if kind == 'ip' else 'whois_domain/'
        params_q = {'q': normalized}
    else:
        endpoint = 'host/'
        # /host accepts both IP and hostname via `host=` param.
        params_q = {'host': normalized}

    url = base + endpoint
    headers = {
        'X-API-Key': key,
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Netlas module',
    }

    try:
        resp = requests.get(url, params=params_q, headers=headers, allow_redirects=False, timeout=(10, 30))
    except requests.RequestException as e:
        log.exception("netlas request failed")
        return {'messages': [{'text': f"Netlas request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Netlas: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Netlas: rate-limited (HTTP 429). Free-tier quota may be exhausted (~50/month).'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"Netlas: no record for `{normalized}` ({sub})."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Netlas returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("netlas returned non-JSON")
        return {'messages': [{'text': 'Netlas returned a non-JSON response.'}]}

    data = _extract_data(payload)
    if not data:
        return {'messages': [{'text': f"Netlas: no record for `{normalized}` ({sub})."}]}

    if sub == 'whois':
        text = _format_whois(normalized, kind, data)
    else:
        text = _format_host(normalized, kind, data, max_ports, max_domains)

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
