#!/usr/bin/env python3

import collections
import requests

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
import logging
from commands import cmdutils

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

@cmdutils.handles(cmdutils.IP, cmdutils.IPV6)
def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': 'You must specify an IP address!'}]}
    query, querytype = cmdutils.classify(params[0])
    if querytype not in (cmdutils.IP, cmdutils.IPV6):
        return {'messages': [{'text': 'You must specify an IP address!'}]}
    headers = {
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for VPNDetection v1.0',
    }
    if settings.APIURL['vpndetection'].get('key'):
        headers['Authorization'] = f"Bearer {settings.APIURL['vpndetection']['key']}"
    try:
        apiurl = settings.APIURL['vpndetection']['url'] + query
        with requests.get(apiurl, headers=headers, timeout=(10, 30)) as response:
            if response.status_code != 200:
                messages.append({'text': 'Failed VPNDetection lookup, check address validity or try again later ...'})
                return {'messages': messages}
            json_response = response.json()
        message = f"**VPNDetection for:** `{query}`\n\n"
        detectionfields = collections.OrderedDict({
            'is_vpn': 'VPN',
            'is_tor': 'TOR',
            'is_relay': 'Privacy Relay',
            'is_bogon': 'Bogon',
        })
        message += f"| Detection Information | `{query}` |\n"
        message += "| :- | -: |\n"
        for detectionfield in detectionfields:
            if detectionfield in json_response:
                result = ":exclamation:" if json_response[detectionfield] else ":heavy_minus_sign:"
                message += f"| **{detectionfields[detectionfield]}** | {result} |\n"
        message += "\n\n"
        network = json_response.get('asn') or {}
        networkfields = collections.OrderedDict({
            'type': 'Host Type',
            'prefix': 'CIDR',
            'asn': 'ASN',
            'name': 'Organisation',
            'domain': 'Domain',
        })
        rows = ""
        for networkfield in networkfields:
            if network.get(networkfield):
                rows += f"| **{networkfields[networkfield]}** | `{network[networkfield]}` |\n"
        if rows:
            message += f"| Network Information | `{query}` |\n| :- | -: |\n" + rows + "\n\n"
        location = json_response.get('location') or {}
        rows = ""
        if location.get('country'):
            rows += f"| **Country** | :flag-{location['country'].lower()}: `{location.get('country_name', '')}` |\n"
        if location.get('timezone'):
            rows += f"| **Timezone** | `{location['timezone']}` |\n"
        if rows:
            message += f"| Location Information | `{query}` |\n| :- | -: |\n" + rows + "\n\n"
        messages.append({'text': message})
    except Exception:
        # Never interpolate the exception into the channel: with a key set, it may carry the request.
        log.exception("vpndetection module error")
        messages.append({'text': 'The VPNDetection lookup failed; see the bot log for details.'})
    finally:
        return {'messages': messages}
