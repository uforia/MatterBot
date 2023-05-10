#!/usr/bin/env python3

import collections
import re
import requests
import urllib.parse
from pathlib import Path
try:
    from commands.sslmate import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/sslmate/settings.py').is_file():
        try:
            from commands.sslmate import settings
        except ModuleNotFoundError: # local test run
            import settings


def process(command, channel, username, params):
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
                    else:
                        messages.append('No results for SSLMate Certificate Transparency lookup of: `%s`' % (params,)})
            else:
                messages.append({'text': 'SSLMate: `%s` is not a valid domain name!' % (params,)})
        except Exception as e:
            messages.append({'text': "An error occurred querying the SSLMate Certificate Transparency API for `%s`:\nError: `%s`" % (params, str(e))})
        finally:
            return {'messages': messages}
