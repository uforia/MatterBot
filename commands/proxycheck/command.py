#!/usr/bin/env python3

import collections
import datetime
import re
import requests
import traceback

### Dynamic configuration loader (do not change/edit)
import importlib
from pathlib import Path
_pkg_name = Path(__file__).parent.name
try:
    defaults_mod = importlib.import_module(f'commands.{_pkg_name}.defaults')
except ModuleNotFoundError:
    try:
        defaults_mod = importlib.import_module('defaults')
    except ModuleNotFoundError:
        print(f"Module {_pkg_name} could not be loaded due to a missing default configuration.")
try:
    settings_mod = importlib.import_module(f'commands.{_pkg_name}.settings')
except ModuleNotFoundError:
    try:
        settings_mod = importlib.import_module('settings')
    except ModuleNotFoundError:
        settings_mod = None
settings = {k: v for k, v in vars(defaults_mod).items() if not k.startswith('__')}
if settings_mod:
    settings.update({k: v for k, v in vars(settings_mod).items() if not k.startswith('__')})
from types import SimpleNamespace
settings = SimpleNamespace(**settings)
### Loader end, actual module functionality starts here

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    stripchars = r'\[\]\n\r\'\"|'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    headers = {
        #'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for ProxyCheck v1.0',
    }
    if len(params):
        query = params[0].lower().replace('[','').replace(']','')
        try:
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", query) or \
               re.search(r"^((?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,7}:|:(?::[0-9A-Fa-f]{1,4}){1,7}|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,5}(?::[0-9A-Fa-f]{1,4}){1,2}|(?:[0-9A-Fa-f]{1,4}:){1,4}(?::[0-9A-Fa-f]{1,4}){1,3}|(?:[0-9A-Fa-f]{1,4}:){1,3}(?::[0-9A-Fa-f]{1,4}){1,4}|(?:[0-9A-Fa-f]{1,4}:){1,2}(?::[0-9A-Fa-f]{1,4}){1,5}|[0-9A-Fa-f]{1,4}:(?:(?::[0-9A-Fa-f]{1,4}){1,6})|:(?:(?::[0-9A-Fa-f]{1,4}){1,6}))$", query):
                querytype = 'ips'
            elif re.search(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", query):
                querytype = 'email'
            else:
                querytype = None
                messages.append({'text': 'You must specify an IP address or email address!'})
            if querytype:
                apiurl = settings.APIURL['proxycheck']['url']
                postdata = {
                    'ips':  f"{query}",
                }
                if 'key' in settings.APIURL['proxycheck']:
                    if settings.APIURL['proxycheck']['key']:
                        apiurl += f"?key={settings.APIURL['proxycheck']['key']}"
                with requests.post(apiurl, headers=headers, data=postdata) as response:
                    if response.status_code in (400,401,402,403,):
                        messages.append({'text': "Failed ProxyCheck lookup, check address validity or try again later ..."})
                    if response.status_code in (200,):
                        json_response = response.json()
                        if query in json_response:
                            message = f"**ProxyCheck for:** `{query}`\n"
                            if 'last_updated' in json_response[query]:
                                datetime_object = datetime.datetime.strptime(json_response[query]['last_updated'], "%Y-%m-%dT%H:%M:%SZ")
                                result = datetime_object.strftime("%B %d, %Y at %H:%M:%S UTC")
                                message += f"**Last updated:** `{result}`\n"
                            message += "\n"
                            if 'network' in json_response[query]:
                                networkfields = collections.OrderedDict({
                                    'type': 'Host Type',
                                    'hostname': 'Hostname',
                                    'range': 'CIDR',
                                    'asn': 'ASN',
                                    'organisation': 'Organisation',
                                    'provider': 'ISP',
                                })
                                message += f"| Network Information | `{query}` |\n"
                                message += "| :- | -: |\n"
                                for networkfield in networkfields:
                                    if networkfield in json_response[query]['network']:
                                        result = f"`{json_response[query]['network'][networkfield]}`"
                                        message += f"| **{networkfields[networkfield]}** | {result} |\n"
                                message += "\n\n"
                            if 'location' in json_response[query]:
                                locationfields = collections.OrderedDict({
                                    'city_name': 'City',
                                    'region_name': 'Region',
                                    'postal_code': 'ZIP code',
                                    'country_code': 'Country',
                                    'latitude': 'GPS',
                                    'longitude': 'GPS',
                                    'timezone': 'Timezone',
                                })
                                message += f"| Location Information | `{query}` |\n"
                                message += "| :- | -: |\n"
                                for locationfield in locationfields:
                                    result = None
                                    if locationfield in json_response[query]['location']:
                                        if locationfield in ('country_code',):
                                            result = f":flag-{json_response[query]['location'][locationfield].lower()}:"
                                        elif locationfield in ('latitude',):
                                            result = None
                                        elif locationfield in ('longitude',):
                                            latitude = json_response[query]['location']['latitude']
                                            longitude = json_response[query]['location']['longitude']
                                            result = f"[OpenStreetMap](https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=12)"
                                        else:
                                            result = f"`{json_response[query]['location'][locationfield]}`"
                                        if result:
                                            message += f"| **{locationfields[locationfield]}** | {result} |\n"
                                message += "\n\n"
                            if 'detections' in json_response[query]:
                                detectionfields = {
                                    'proxy': 'Proxy',
                                    'vpn': 'VPN',
                                    'compromised': 'Compromised',
                                    'scraper': 'Scraper',
                                    'tor': 'TOR',
                                    'hosting': 'Hosting',
                                    'anonymous': 'Anonymous',
                                    'disposable': 'Disposable',
                                    'risk': 'Risk Score',
                                }
                                message += f"| Detection Information | `{query}` |\n"
                                message += "| :- | -: |\n"
                                for detectionfield in detectionfields:
                                    result = None
                                    if detectionfield in json_response[query]['detections']:
                                        if not detectionfield in ('risk',):
                                            if json_response[query]['detections'][detectionfield]:
                                                result = ":exclamation:"
                                            else:
                                                result = ":heavy_minus_sign:"
                                        else:
                                            risk = json_response[query]['detections'][detectionfield]
                                            if risk<33:
                                                result = ":white_check_mark:"
                                            if risk>=33 and risk<75:
                                                result = ":warning:"
                                            if risk>=75:
                                                result = ":x:"
                                    if result:
                                        message += f"| **{detectionfields[detectionfield]}** | {result} |\n"
                                message += "\n\n"
                            if len(message):
                                messages.append({'text': message})
        except:
            messages.append({'text': 'An error occurred in the ProxyCheck module:\nError: `%s`' % (traceback.format_exc(),)})
        finally:
            return {'messages': messages}
