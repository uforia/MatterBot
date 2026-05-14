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

# CVE-YYYY-NNNN+ — uppercase normalised; 4-digit year then 4-or-more-digit sequence.
CVE_RE = re.compile(r'^CVE-(\d{4})-(\d{4,8})$', re.IGNORECASE)


def _normalize_cve(raw):
    if not raw:
        return None
    m = CVE_RE.match(raw.strip())
    if not m:
        return None
    return f"CVE-{m.group(1)}-{m.group(2)}"


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _pick_description(cve_obj):
    """Return the first English description from a NIST-NVD shape."""
    descs = cve_obj.get('descriptions') or []
    if not isinstance(descs, list):
        return None
    for d in descs:
        if isinstance(d, dict) and d.get('lang') == 'en':
            return d.get('value')
    if descs and isinstance(descs[0], dict):
        return descs[0].get('value')
    return None


def _pick_cvss(cve_obj):
    """Return (score, severity, vector) from the highest-version CVSS metric available."""
    metrics = cve_obj.get('metrics') or {}
    for key in ('cvssMetricV40', 'cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2'):
        bucket = metrics.get(key) or []
        if not isinstance(bucket, list) or not bucket:
            continue
        cvss = (bucket[0] or {}).get('cvssData') or {}
        score = cvss.get('baseScore')
        severity = cvss.get('baseSeverity') or (bucket[0] or {}).get('baseSeverity')
        vector = cvss.get('vectorString')
        if score is not None or severity or vector:
            label = {
                'cvssMetricV40': 'v4.0',
                'cvssMetricV31': 'v3.1',
                'cvssMetricV30': 'v3.0',
                'cvssMetricV2':  'v2',
            }[key]
            return label, score, severity, vector
    return None, None, None, None


def _pick_cwes(cve_obj):
    cwes = []
    weaknesses = cve_obj.get('weaknesses') or []
    for w in weaknesses:
        for d in (w.get('description') or []):
            v = d.get('value')
            if v and v.startswith('CWE-') and v not in cwes:
                cwes.append(v)
    return cwes


def _pick_references(cve_obj, cap):
    refs = []
    for r in cve_obj.get('references') or []:
        if isinstance(r, dict) and r.get('url'):
            refs.append(r['url'])
        elif isinstance(r, str):
            refs.append(r)
        if len(refs) >= cap:
            break
    return refs


def _extract_cve_object(payload):
    """VulnCheck wraps the NVD payload — accept a few shapes defensively."""
    if not isinstance(payload, dict):
        return None
    # Direct: payload['cve']
    if isinstance(payload.get('cve'), dict):
        return payload['cve']
    # Nested under data: payload['data']['cve'] or payload['data'][0]['cve']
    data = payload.get('data')
    if isinstance(data, dict):
        if isinstance(data.get('cve'), dict):
            return data['cve']
        # VulnCheck sometimes returns the NVD record directly under 'data'.
        if 'id' in data and ('descriptions' in data or 'metrics' in data):
            return data
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            if isinstance(first.get('cve'), dict):
                return first['cve']
            if 'id' in first and ('descriptions' in first or 'metrics' in first):
                return first
    return None


def _format_cve(cve_id, cve_obj, exploits, max_refs, max_desc):
    rows = []

    cvss_label, score, severity, vector = _pick_cvss(cve_obj)
    if score is not None or severity:
        bits = []
        if score is not None:
            bits.append(f"{score}")
        if severity:
            bits.append(str(severity))
        rows.append((f"CVSS {cvss_label}" if cvss_label else 'CVSS', ' / '.join(bits)))
        if vector:
            rows.append(('Vector', vector))

    cwes = _pick_cwes(cve_obj)
    if cwes:
        rows.append(('Weakness', ', '.join(cwes[:8])))

    published = cve_obj.get('published') or cve_obj.get('publishedDate')
    if published:
        rows.append(('Published', published))
    modified = cve_obj.get('lastModified') or cve_obj.get('lastModifiedDate')
    if modified:
        rows.append(('Modified', modified))

    if exploits is not None:
        rows.append(('Known exploits', str(exploits)))

    desc = _pick_description(cve_obj)
    if desc and len(desc) > max_desc:
        desc = desc[:max_desc - 1].rstrip() + '…'

    lines = [f"VulnCheck record for `{cve_id}`:"]
    if desc:
        # Render description as quoted prose so the table that follows still parses.
        for line in desc.splitlines():
            lines.append(f"> {line.strip()}")
        lines.append('')
    if rows:
        lines.append('| Field | Value |')
        lines.append('| :- | :- |')
        for k, v in rows:
            lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    refs = _pick_references(cve_obj, max_refs)
    if refs:
        lines.append('')
        lines.append('**References:**')
        for r in refs:
            lines.append(f"- {r}")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    cve_id = _normalize_cve(raw)
    if not cve_id:
        return {'messages': [{'text': f"VulnCheck: `{raw}` is not a valid CVE identifier (expected `CVE-YYYY-NNNN+`)."}]}

    cfg = getattr(settings, 'APIURL', {}).get('vulncheck', {})
    token = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_refs = int(getattr(settings, 'MAX_REFERENCES', 8))
    max_desc = int(getattr(settings, 'MAX_DESC_CHARS', 800))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not token or token.startswith('<'):
        return {'messages': [{'text': 'VulnCheck is not configured. Set `key` in `settings.py` (https://vulncheck.com/).'}]}

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot VulnCheck module',
    }

    # CVE detail — vulncheck-nvd2 enriches with VulnCheck data; if that scope
    # isn't on the free tier we fall back to the upstream NIST-NVD2 mirror.
    detail_payload = None
    detail_endpoints = [
        f"index/vulncheck-nvd2/{cve_id}",
        f"index/nist-nvd2/{cve_id}",
    ]
    last_status = None
    for endpoint in detail_endpoints:
        try:
            resp = requests.get(
                base + endpoint,
                headers=headers,
                allow_redirects=False,
                timeout=(10, 30),
            )
        except requests.RequestException as e:
            log.exception("vulncheck request failed")
            return {'messages': [{'text': f"VulnCheck request failed: `{e}`"}]}
        last_status = resp.status_code
        if resp.status_code == 200:
            try:
                detail_payload = resp.json()
            except ValueError:
                log.exception("vulncheck returned non-JSON")
                return {'messages': [{'text': 'VulnCheck returned a non-JSON response.'}]}
            break
        if resp.status_code == 401:
            return {'messages': [{'text': 'VulnCheck: authentication failed — check API token.'}]}
        if resp.status_code == 403:
            # Token doesn't have access to this index — try the next one.
            continue
        if resp.status_code == 404:
            # CVE not present in this index — try the next one.
            continue
        # 429 / 5xx — surface clearly without trying alternates.
        return {'messages': [{'text': f"VulnCheck returned HTTP {resp.status_code}."}]}

    if detail_payload is None:
        if last_status == 404:
            return {'messages': [{'text': f"VulnCheck: no record for `{cve_id}`."}]}
        if last_status == 403:
            return {'messages': [{'text': 'VulnCheck: API token does not have access to the CVE indexes (free tier may not include vulncheck-nvd2).'}]}
        return {'messages': [{'text': f"VulnCheck: lookup failed (last HTTP {last_status})."}]}

    cve_obj = _extract_cve_object(detail_payload)
    if not cve_obj:
        return {'messages': [{'text': f"VulnCheck: unrecognised response shape for `{cve_id}`."}]}

    # Optional: count known exploits. Failure is non-fatal.
    exploits_count = None
    try:
        eresp = requests.get(
            base + 'index/exploits',
            params={'cve': cve_id, 'limit': 1},
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
        )
        if eresp.status_code == 200:
            ejson = eresp.json()
            meta = ejson.get('_meta') if isinstance(ejson, dict) else None
            if isinstance(meta, dict):
                exploits_count = meta.get('total_documents') or meta.get('total')
            if exploits_count is None and isinstance(ejson, dict):
                data = ejson.get('data')
                if isinstance(data, list):
                    exploits_count = len(data)
    except (requests.RequestException, ValueError):
        log.debug("vulncheck exploits lookup soft-failed; continuing without exploit count")

    text = _format_cve(cve_id, cve_obj, exploits_count, max_refs, max_desc)
    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
