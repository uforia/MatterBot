#!/usr/bin/env python3

import collections
import re
import requests
import urllib.parse

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
        messages = []
        params = params[0].replace('[.]','.')
        try:
            # Domain or URL?
            hostname = None
            if re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", params):
                hostname = params
            elif params.startswith('http'):
                try:
                    parsed_url = urllib.parse.urlparse(params)
                    hostname = parsed_url.netloc
                except:
                    messages.append({'text': 'SSLMate: `%s` is not a valid domain name!' % (params,)})
            if hostname:
                fieldNames = collections.OrderedDict({
                    'dns_names': 'Hostname(s)',
                    'issuer': 'Certificate Authority',
                    'cert_sha256': 'SHA256 hash',
                    'revoked': 'Revocation Status',
                })
                message = 'SSLMate Certificate Transparency lookup for `%s`:' % (params,)
                endpoint = settings.APIURL['sslmate']['url']+hostname
                if len(settings.EXPANDFIELDS):
                    endpoint += '&expand=' + '&expand='.join(settings.EXPANDFIELDS)
                apikey = settings.APIURL['sslmate']['key']
                headers = {
                    'Authorization': 'Bearer %s' % apikey,
                    'Content-Type': settings.CONTENTTYPE,
                }
                with requests.get(endpoint, headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        if 'code' in json_response:
                            if json_response['code'] != 'service_outage':
                                message += '\n\n'
                                for fieldName in fieldNames:
                                    message += '| '+fieldNames[fieldName]+' '
                                message += '|\n'
                                message += '| :- '*len(fieldNames)
                                message += '|\n'
                                for id in json_response:
                                    for fieldName in fieldNames:
                                        if fieldName in id:
                                            if isinstance(id[fieldName], list):
                                                fieldContents = ', '.join(id[fieldName])
                                            else:
                                                fieldContents = id[fieldName]
                                            if fieldName == 'issuer':
                                                fieldContents = id[fieldName]['friendly_name']
                                            if fieldName == 'revoked':
                                                fieldContents = '**Revoked**' if id[fieldName] else 'Not revoked'
                                            message += '| %s ' % fieldContents
                                        else:
                                            message += '| - '
                                    message += '|\n'
                                message += '|\n\n'
                                messages.append({'text': message})
        except Exception as e:
            messages.append({'text': "An error occurred querying the SSLMate Certificate Transparency API for `%s`:\nError: `%s`" % (params, str(e))})
        finally:
            return {'messages': messages}
