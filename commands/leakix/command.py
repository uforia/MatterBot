#!/usr/bin/env python3

import datetime
import json
import random
import re
import requests
import traceback
import urllib.parse
from pathlib import Path
try:
    from commands.leakix import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/leakix/settings.py').is_file():
        try:
            from commands.leakix import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    messages = []
    querytypes = ['domain','host','subdomains']
    stripchars = '`\[\]\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    try:
        if len(params)>0:
            message = ''
            query = regex.sub('',params[0].lower())
            endpoints = None
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", query):
                endpoints = ['host/']
            elif re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", query):
                endpoints = ['host/']
            elif re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", query):
                endpoints = ['domain/', 'api/subdomains/']
            elif 'http' in query:
                query = query.split('://')[1].split('/')[0]
                endpoints = ['domain/', 'api/subdomains/']
            if endpoints:
                headers = {
                    'accept': settings.CONTENTTYPE,
                    'api-key': '%s' % random.choice(settings.APIURL['leakix']['key']),
                }
                for endpoint in endpoints:
                    query = urllib.parse.quote_plus(query.encode())
                    APIENDPOINT = settings.APIURL['leakix']['url']+endpoint+query
                    with requests.get(APIENDPOINT,headers=headers) as response:
                        json_response = response.json()
                        querytype = endpoint.strip('/')
                        if json_response:
                            if 'subdomains' in APIENDPOINT:
                                if len(json_response)>0:
                                    count = 0
                                    fieldnames = {
                                        'subdomain': 'Subdomain',
                                        'distinct_ips': 'Unique IPs',
                                        'last_seen': 'Last Seen',
                                    }
                                    title = True
                                    if title:
                                        message = '| **LeakIX `%s` lookup** |' % (query,)
                                        for fieldname in fieldnames:
                                            message += ' **%s** |' % (fieldnames[fieldname])
                                        message += '\n'
                                        message += '| -: |'
                                        message += ':- |'*(len(fieldnames))
                                        title = False
                                    for subdomain in json_response:
                                        count += 1
                                        if count>10:
                                            message += '\n\nOnly showing first 10 records - check JSON for complete output.'
                                            messages.append({'text': message, 'uploads': [
                                                {'filename': 'LeakIX-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%d')+'.json', 'bytes': response.content}
                                            ]})
                                            break
                                        else:
                                            message += '\n| **Result** `%s` | ' % (count,)
                                            for fieldname in fieldnames:
                                                value = subdomain[fieldname]
                                                message += '`%s` |' % (value,)
                                if count>0 and count<=10:
                                    message += '\n\n'
                                    messages.append({'text': message})
                            if 'Services' in json_response:
                                if json_response['Services']:
                                    fieldnames = {
                                        'host': 'Hostname',
                                        'ip': 'IP',
                                        'reverse': 'Reverse',
                                        'protocol': 'Protocol',
                                        'port': 'Port',
                                        'leak': 'Vulnerable',
                                        'summary': 'Content',
                                    }
                                    count = 0
                                    title = True
                                    for service in json_response['Services']:
                                        if 'leak' in service:
                                            if len(service['leak']['severity'])>0:
                                                count += 1
                                                if title:
                                                    message = '| **LeakIX `%s` lookup** |' % (query,)
                                                    for fieldname in fieldnames:
                                                        message += ' **%s** |' % (fieldnames[fieldname])
                                                    message += '\n'
                                                    message += '| -: |'
                                                    message += ':- |'*(len(fieldnames))
                                                    title = False
                                                message += '\n| **Result** `%s` | ' % (count,)
                                                for fieldname in fieldnames:
                                                    value = service[fieldname]
                                                    if len(service[fieldname])>0:
                                                        if fieldname == 'leak':
                                                            value = service['leak']['severity'].title()
                                                        if fieldname == 'protocol':
                                                            value = value.upper()
                                                            if 'ssl' in service:
                                                                if 'enabled' in service['ssl']:
                                                                    if service['ssl']['enabled']:
                                                                        value += ' (SSL/TLS)'
                                                        if fieldname == 'summary':
                                                            value = regex.sub(' ',value)
                                                            if len(value)>60:
                                                                value = value[:60] + ' [...]'
                                                        if not len(value)>0:
                                                            value = '-'
                                                        message += '`%s` |' % (value,)
                                        message += '\n'
                                        if count>=10:
                                            message += '\n\nOnly showing first 10 records - check JSON for complete output.'
                                            messages.append({'text': message, 'uploads': [
                                                {'filename': 'LeakIX-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%d')+'.json', 'bytes': response.content}
                                            ]})
                                            break
                                    if count>0 and count<=10:
                                        message += '\n\n'
                                        messages.append({'text': message})
                            if 'Leaks' in json_response:
                                if json_response['Leaks']:
                                    fieldnames = {
                                        'host': 'Hostname',
                                        'ip': 'IP',
                                        'reverse': 'Reverse',
                                        'protocol': 'Protocol',
                                        'port': 'Port',
                                        'leak': 'Vulnerable',
                                        'summary': 'Content',
                                    }
                                    count = 0
                                    title = True
                                    for leak in json_response['Leaks']:
                                        count += 1
                                        if title:
                                            message = '| **LeakIX `%s` lookup** |' % (query,)
                                            for fieldname in fieldnames:
                                                message += ' **%s** |' % (fieldnames[fieldname])
                                            message += '\n'
                                            message += '| -: |'
                                            message += ':- |'*(len(fieldnames))
                                            title = False
                                        for event in leak['events']:
                                            line = ''
                                            for fieldname in fieldnames:
                                                if len(event[fieldname])>0:
                                                    value = event[fieldname]
                                                    if fieldname == 'leak':
                                                        value = event['leak']['severity'].title()
                                                        if not len(value):
                                                            value = '-'
                                                    if fieldname == 'protocol':
                                                        value = value.upper()
                                                        if 'ssl' in event:
                                                            if 'enabled' in event['ssl']:
                                                                if event['ssl']['enabled']:
                                                                    value += ' (SSL/TLS)'
                                                    if fieldname == 'summary':
                                                        value = regex.sub(' ',value)
                                                        if len(value)>60:
                                                            value = value[:60] + ' [...]'
                                                else:
                                                    value = '-'
                                                line += '`%s` |' % (value,)
                                            if line not in message:
                                                message += '\n| **Result** `'+str(count)+'` | '+line
                                        if count>=settings.LEAKLIMIT:
                                            message += '\n\nOnly showing first '+str(settings.LEAKLIMIT)+' records - check JSON for complete output.'
                                            messages.append({'text': message, 'uploads': [
                                                {'filename': 'LeakIX-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%d')+'.json', 'bytes': response.content}
                                            ]})
                                            break
                                    if count>0 and count<settings.LEAKLIMIT:
                                        message += '\n\n'
                                        messages.append({'text': message})
    except Exception as e:
        print(traceback.format_exc())
        messages.append({'text': 'A Python error occurred searching LeakIX:\nError:' + str(e)})
    finally:
        return {'messages': messages}