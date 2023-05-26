#!/usr/bin/env python3

import collections
import datetime
import json
import math
import random
import re
import requests
import string
from pathlib import Path
try:
    from commands.censys import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/censys/settings.py').is_file():
        try:
            from commands.censys import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params):
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    if len(params)>0:
        querytype = params[0]
        if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", querytype.replace('[', '').replace(']', '')):
            params = [querytype]
            querytype = 'ip'
        elif re.search(r"^[A-Fa-f0-9]{64}$", querytype.replace('[', '').replace(']', '')):
            params = [querytype]
            querytype = 'cert'
        else:
            params = params[1:]
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        try:
            messages = []
            if querytype == 'ip':
                ip = params[0].split(':')[0].replace('[', '').replace(']', '')
                if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", ip):
                    text = 'Censys `%s` search for `%s`: ' % (querytype, ip)
                    APIENDPOINT = settings.APIURL['censys']['url'] + '/hosts/%s' % (ip,)
                    with requests.get(APIENDPOINT, auth=(settings.APIURL['censys']['key'], settings.APIURL['censys']['secret']), headers=headers) as response:
                        json_response = response.json()
                        if 'error' in json_response:
                            error = json_response['error']
                            return {'messages': [{'text': 'An error occurred searching Censys: ' + error}]}
                        if 'result' in json_response:
                            result = json_response['result']
                            services = None
                            dns = None
                            if 'services' in result:
                                services = result['services']
                                if len(services):
                                    fieldmap = collections.OrderedDict({
                                        '_decoded': 'Service',
                                        'port': 'Port',
                                        'transport_protocol': 'Proto',
                                        'tls': 'SSL/TLS',
                                        'software': 'Product',
                                        'banner': 'Banner',
                                    })
                                    text += '\n\n'
                                    for key in fieldmap:
                                        text += '| %s ' % (fieldmap[key])
                                    text += '|\n'
                                    text += '| -:| -:| -:| -:|:- |:- |\n'
                                    for service in services:
                                        for field in fieldmap:
                                            value = None
                                            if field in service:
                                                value = service[field]
                                                if field == '_decoded' and service[field] == 'banner_grab':
                                                    value = '`unknown`'
                                                else:
                                                    try:
                                                        value = ' `'+''.join([_ for _ in value if _.isprintable()])+'`'
                                                        value = regex.sub(' ', value)
                                                        if len(value)>60:
                                                            value = '`'+value[:60]+'`[...]'
                                                    except (UnicodeDecodeError, AttributeError, TypeError):
                                                        pass
                                                if field == 'tls':
                                                    value = service[field]['version_selected']
                                                if field == 'software':
                                                    softwares = set()
                                                    for software in service['software']:
                                                        if 'product' in software:
                                                            softwares.add(software['product'])
                                                    if len(softwares):
                                                        value = ', '.join(softwares)
                                            if not value:
                                                value = '-'
                                            text += '| %s ' % (value,)
                                        text += '|\n'
                            if 'dns' in result:
                                text += '\n\n---\n\n'
                                dns = result['dns']
                                if 'records' in dns:
                                    records = dns['records']
                                    text += '**Associated DNS records**: '
                                    for record in records:
                                        type = records[record]['record_type']
                                        text += '`%s` (%s), ' % (record, type)
                                    text = text[:-2]
                                    text += '\n'
                                if 'reverse_dns' in dns:
                                    reverses = dns['reverse_dns']['names']
                                    text += '**Reverse DNS names**: `' + '`, `'.join(reverses) + '`\n'
                            if dns or services:
                                messages.append({'text': text})
                                messages.append({'text': 'Censys JSON output:', 'uploads': [
                                                    {'filename': 'censys-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content}
                                                ]})
                            else:
                                text += 'no results found.'
                                messages.append({'text': text})
                else:
                    text += ' invalid IP address!'
                    messages.append({'text': text})
            if querytype == 'cert':
                sha256 = params[0]
                if (re.search(r"^[A-Fa-f0-9]{64}$", sha256)):
                    text = '\nCensys SHA256 certificate fingerprint search for: `%s`' % (sha256,)
                    APIENDPOINT = settings.APIURL['censys']['url'] + '/certificates/' + sha256 + '/hosts'
                    with requests.get(APIENDPOINT, auth=(settings.APIURL['censys']['key'], settings.APIURL['censys']['secret']), headers=headers) as response:
                        json_response = response.json()
                        if 'error' in json_response:
                            error = json_response['error']
                            return {'messages': [{'text': 'An error occurred, wrong/missing API key? Error: ' + error}]}
                        if 'result' in json_response:
                            uploads = []
                            result = json_response['result']
                            if 'hosts' in result:
                                hosts = result['hosts']
                                if len(hosts):
                                    if len(hosts)>10:
                                        text += '\n*Note: only returning first 10 results!*'
                                    text += '\n\n'
                                    fieldmap = collections.OrderedDict({
                                        'name': 'Hostname',
                                        'ip': 'IP address',
                                        'first_observed_at': 'First seen',
                                        'observed_at': 'Last seen',
                                    })
                                    for field in fieldmap:
                                        text += '| %s ' % (fieldmap[field])
                                    text += '|\n'
                                    text += '|:- | -:| -:| -:|\n'
                                    cursor = '_firstpage'
                                    count = 0
                                    page = 1
                                    while count < 10 and count < len(hosts):
                                        host = hosts[count]
                                        for field in fieldmap:
                                            if field in host:
                                                text += '| %s ' % (host[field])
                                            else:
                                                text += '| - '
                                        text += '|\n'
                                        count += 1
                                    uploads.append({'filename': 'censys-'+querytype+'-page-'+str(page)+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content})
                                    while cursor:
                                        if 'links' in result:
                                            if result['links']['next']:
                                                page += 1
                                                cursor = result['links']['next']
                                                APIENDPOINT = settings.APIURL['censys']['url'] + '/certificates/' + sha256 + '/hosts&cursor=' + cursor
                                                response = requests.get(APIENDPOINT, auth=(settings.APIURL['censys']['key'], settings.APIURL['censys']['secret']))
                                                json_response = response.json()
                                                if 'result' in json_response:
                                                    uploads.append({'filename': 'censys-'+querytype+'-page-'+str(page)+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content})
                                                    result = json_response['result']
                                                    if 'hosts' in result:
                                                        hosts = result['hosts']
                                                else:
                                                    cursor = None
                                            else:
                                                cursor = None
                                    messages.append({'text': text})
                                    messages.append({'text': 'Censys JSON output:', 'uploads': uploads})
                                else:
                                    text += 'no results.'
                                    messages.append({'text': text})

                else:
                    messages.append({'text': 'Censys error: invalid SHA256 fingerprint `%s`' % (params,)})
            if querytype == 'credits' or querytype == 'account':
                APIENDPOINT = settings.APIURL['censys']['url'].replace('/v2', '/v1') + '/account'
                with requests.get(APIENDPOINT, auth=(settings.APIURL['censys']['key'], settings.APIURL['censys']['secret']), headers=headers) as response:
                    json_response = response.json()
                    if 'error' in json_response:
                        error = json_response['error']
                        return {'messages': [{'text': 'An error occurred, wrong/missing API key? Error: ' + error}]}
                    text = 'Censys account information for: '
                    quota = json_response['quota']
                    email = json_response['email']
                    query_credits_used = str(quota['used'])
                    query_credits_allowance = str(quota['allowance'])
                    query_credits_reset = quota['resets_at']
                    text += '`' + email + '`'
                    text += '\n**Credits (used/limit)**: ' + query_credits_used + '/' + query_credits_allowance
                    text += '\n**Next reset at**: ' + query_credits_reset
                    messages.append({'text': text})
            return {'messages': messages}
        except Exception as e:
            return {'messages': [
                {'text': 'A Python error occurred searching Censys:\nError:'+str(e)}
            ]}
    else:
        return {'messages': [
            {'text': 'Specify a Censys query type: `' + '`, `'.join(querytypes) + '`'}
        ]}
