#!/usr/bin/env python3

import re
import requests

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
        params = params[0].replace('[.]','.')
        try:
            data = None
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", params):
                data = params.split(':')[0]
            if data:
                with requests.get(settings.APIURL['ipwhois']['url'] + data) as response:
                    json_response = response.json()
                    message = 'IPWHOIS lookup for `%s`' % (data,)
                    if 'success' in json_response:
                        if json_response['success'] != True:
                            return {'messages': [
                                {'text': 'IPWHOIS errored out while searching for `%s`' % (params,)}
                            ]}
                        if 'connection' in json_response:
                            if 'isp' in json_response['connection']:
                                message += ' | ISP: `' + json_response['connection']['isp'] + '`'
                            if 'asn' in json_response['connection']:
                                asn = json_response['connection']['asn']
                                if asn != 0:
                                    message += ', ASN `' + str(asn) + '`'
                        if 'city' in json_response:
                            message += ' | Geo: `' + json_response['city'] + '`'
                        if 'country' in json_response:
                            message += ', `' + json_response['country'] + '`'
                        if 'flag' in json_response:
                            if 'emoji' in json_response['flag']:
                                message += ' ' + json_response['flag']['emoji']
                        if 'continent' in json_response:
                                message += ', `' + json_response['continent'] + '`'
                        return {'messages': [
                            {'text': message.strip()},
                        ]}
        except Exception as e:
            return {'messages': [
                {'text': "An error occurred searching IPWHOIS for `%s`:\nError: `%s`" % (params, e.message)},
            ]}
