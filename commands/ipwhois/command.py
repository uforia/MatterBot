#!/usr/bin/env python3

import re
import requests

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
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
