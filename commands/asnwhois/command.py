#!/usr/bin/env python3

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
    if len(params)>0:
        params = params[0]
        try:
            data = None
            if re.search(r"^[0-9]+$", params):
                data = params
            if data:
                headers = {
                    'Content-Type': settings.CONTENTTYPE,
                    'User-Agent': 'MatterBot integration for ASNWHOIS v0.1'
                }
                url = settings.APIURL['asnwhois']['url']+f"{data}"
                with requests.get(settings.APIURL['asnwhois']['url']+f"{data}", headers=headers) as response:
                    json_response = response.json()
                    message = 'ASN WHOIS lookup for `%s`: ' % (data,)
                    if 'data' in json_response:
                        if json_response['data']['asn'] == None:
                            return {'messages': [
                                {'text': 'ASN `%s` does not exist.' % (data,)}
                            ]}
                        else:
                            jsondata = json_response['data']['asn']
                            name = jsondata['asnName']
                            source = jsondata['source']
                            country = jsondata['country']['iso']
                            peers = str(jsondata['asnDegree']['peer'])
                            providers = str(jsondata['asnDegree']['provider'])
                            lat = str(jsondata['latitude'])
                            long = str(jsondata['longitude'])
                            gpsurl = settings.APIURL['osmdata']['url']+f"lat={lat}&lon={long}&format=json"
                            with requests.get(gpsurl, headers=headers) as response:
                                json_response = response.json()
                                if 'display_name' in json_response:
                                    address = json_response['display_name']
                                else:
                                    address = 'unknown'
                            message += 'Name: `'+name+'`, Address: `'+address+'`, Latitude/Longitude: `'+lat+'`/`'+long+'` :flag-'+country.lower()+':, Peers/Providers: `'+peers+'`/`'+providers+'`, Source: `'+source+'`'
                            return {'messages': [
                                {'text': message.strip()},
                            ]}
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred in GTFOBins:\nError: ' + (str(e),traceback.format_exc())}
            ]}
