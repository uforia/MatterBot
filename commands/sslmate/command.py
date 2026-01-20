#!/usr/bin/env python3

import collections
import re
import requests
import urllib.parse

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
### Loader end, actual module functionality starts heres

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
