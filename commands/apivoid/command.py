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
URL_RE = re.compile(r'^(?:https?|hxxps?)://[^\s\x00-\x1f]{4,2048}$', re.IGNORECASE)


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _validate_ip(raw):
    if not raw:
        return None
    q = raw.strip().replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    return q if _is_ip(q) else None


def _validate_domain(raw):
    if not raw:
        return None
    q = raw.strip().lower().replace('[.]', '.').replace('(.)', '.')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    return q if HOSTNAME_RE.match(q) else None


def _validate_url(raw):
    if not raw:
        return None
    q = raw.strip()
    # Restore defanged URL form before checking.
    q = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    q = re.sub(r'^hxxps?://', lambda m: m.group(0).replace('hxxp', 'http'), q, flags=re.IGNORECASE)
    return q if URL_RE.match(q) else None


# Each subcommand declares its endpoint path, query-param name, validator,
# and label. _format_report() is shape-agnostic and walks the response for
# detection sub-keys.
SUBCOMMANDS = {
    'iprep':     {'endpoint': 'iprep/v1/pay-as-you-go/',     'param': 'ip',   'validator': _validate_ip,     'label': 'IP reputation'},
    'domainrep': {'endpoint': 'domainbl/v1/pay-as-you-go/',  'param': 'host', 'validator': _validate_domain, 'label': 'domain reputation'},
    'urlrep':    {'endpoint': 'urlrep/v1/pay-as-you-go/',    'param': 'url',  'validator': _validate_url,    'label': 'URL reputation'},
    'dnslookup': {'endpoint': 'dnslookup/v1/pay-as-you-go/', 'param': 'host', 'validator': _validate_domain, 'label': 'DNS lookup',
                  'extra': {'action': 'dns-any'}},
}


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format_report(sub, target, label, payload, max_detections):
    if not isinstance(payload, dict):
        return None
    data = payload.get('data')
    if not isinstance(data, dict):
        # APIVoid surfaces auth / credit errors here.
        err = payload.get('error') or payload.get('message')
        if err:
            return f"APIVoid {sub}: `{_cell(err)}`"
        return None

    rows = [('Target', f"{target} ({label})")]
    credits = payload.get('credits_remained')
    if credits is not None:
        rows.append(('Credits remaining', credits))

    # Initialise here so the engines-detection block below can run for any
    # payload shape — some endpoints (dnslookup) have no `report` key at all.
    engines_dict = None
    report = data.get('report')
    if isinstance(report, dict):
        # Best-effort common-field surfacing — APIVoid wraps every endpoint a
        # bit differently. We pull what's present.
        info = report.get('information') or report.get('information_basic') or {}
        if isinstance(info, dict):
            for k_in, k_out in [
                ('country_name', 'Country'),
                ('country_code', 'Country code'),
                ('region_name', 'Region'),
                ('city_name', 'City'),
                ('isp', 'ISP'),
                ('asn_number', 'ASN'),
                ('domain_name', 'Domain'),
                ('domain_age_in_days', 'Domain age (days)'),
                ('registrar_name', 'Registrar'),
            ]:
                v = info.get(k_in)
                if v is not None:
                    rows.append((k_out, v))

        # Detection counts.
        blacklists = report.get('blacklists') or report.get('domain_blacklist') or report.get('url_blacklists') or {}
        detection_count = None
        engine_count = None
        engines_dict = None
        if isinstance(blacklists, dict):
            detection_count = blacklists.get('detections')
            engine_count = blacklists.get('engines_count')
            engines_dict = blacklists.get('engines')
        if detection_count is not None and engine_count is not None:
            rows.append(('Detection ratio', f"{detection_count} / {engine_count}"))

        # Risk score.
        risk = report.get('risk_score') or report.get('site_score')
        if isinstance(risk, dict):
            risk = risk.get('result') or risk.get('score')
        if risk is not None:
            rows.append(('Risk score', risk))

    lines = [f"APIVoid {sub} for `{target}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # Engine detections sub-table (only engines that actually flagged the
    # target). Skip when there's no engines dict.
    if isinstance(engines_dict, dict) and engines_dict:
        detected = []
        for name, eng in engines_dict.items():
            if not isinstance(eng, dict):
                continue
            if eng.get('detected') or eng.get('elapsed') == 'detected':
                detected.append((name, eng))
        if detected:
            total = len(detected)
            shown = detected[:max_detections]
            lines.append('')
            lines.append(f"**Engine detections ({len(shown)} of {total}):**")
            lines.append('| Engine | Reference | Detected |')
            lines.append('| :- | :- | :- |')
            for name, eng in shown:
                ref = eng.get('reference') or eng.get('detected_url') or '—'
                detected_flag = 'yes' if eng.get('detected') else _cell(eng.get('elapsed', '?'))
                lines.append(f"| `{_cell(name)}` | `{_cell(ref)}` | `{detected_flag}` |")
            if total > max_detections:
                lines.append(f"_…{total - max_detections} more engine(s) not shown._")

    # dnslookup has a different output — a `data.records` list.
    records = (data.get('records') if isinstance(data, dict) else None) or []
    if records:
        total = len(records)
        shown = records[:max_detections]
        lines.append('')
        lines.append(f"**DNS records ({len(shown)} of {total}):**")
        lines.append('| Type | Target |')
        lines.append('| :- | :- |')
        for r in shown:
            if not isinstance(r, dict):
                continue
            rtype = r.get('type') or r.get('record_type') or '?'
            value = r.get('target') or r.get('value') or r.get('address') or '?'
            lines.append(f"| `{_cell(rtype)}` | `{_cell(value)}` |")
        if total > max_detections:
            lines.append(f"_…{total - max_detections} more record(s) not shown._")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        cmds = ', '.join(f"`{k}`" for k in SUBCOMMANDS)
        return {'messages': [{'text': f"Usage: `@apivoid <subcommand> <target>`. Subcommands: {cmds}"}]}

    sub = params[0].lower()
    if sub not in SUBCOMMANDS:
        cmds = ', '.join(f"`{k}`" for k in SUBCOMMANDS)
        return {'messages': [{'text': f"APIVoid: unknown subcommand `{_cell(params[0])}`. Subcommands: {cmds}"}]}

    if len(params) < 2:
        return {'messages': [{'text': f"Usage: `@apivoid {sub} <target>` ({SUBCOMMANDS[sub]['label']})"}]}

    cfg_sub = SUBCOMMANDS[sub]
    target_raw = params[1]
    target = cfg_sub['validator'](target_raw)
    if not target:
        return {'messages': [{'text': f"apivoid {sub}: `{_cell(target_raw)}` is not a valid target for {cfg_sub['label']}."}]}

    api = getattr(settings, 'APIURL', {}).get('apivoid', {})
    key = api.get('key') or ''
    base = (api.get('url') or '').rstrip('/') + '/'
    max_detections = int(getattr(settings, 'MAX_DETECTIONS', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'APIVoid is not configured. Set `key` in `settings.py` (https://www.apivoid.com/).'}]}

    url = base + cfg_sub['endpoint']
    qparams = {'key': key, cfg_sub['param']: target}
    qparams.update(cfg_sub.get('extra', {}))

    try:
        resp = requests.get(
            url,
            params=qparams,
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot APIVoid module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        # apikey lives in the query string; str(e) sometimes carries the
        # full URL — echo only the exception class to avoid leaking it.
        log.exception("apivoid request failed")
        return {'messages': [{'text': f"APIVoid request failed: `{type(e).__name__}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'APIVoid: authentication failed — check `key`.'}]}
    if resp.status_code == 402:
        return {'messages': [{'text': 'APIVoid: out of credits (HTTP 402). Top up at the dashboard.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'APIVoid: rate-limited (HTTP 429).'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"APIVoid returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("apivoid returned non-JSON")
        return {'messages': [{'text': 'APIVoid returned a non-JSON response.'}]}

    text = _format_report(sub, target, cfg_sub['label'], payload, max_detections)
    if not text:
        return {'messages': [{'text': f"APIVoid: unrecognised response shape for `{target}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
