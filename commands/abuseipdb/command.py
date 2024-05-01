#!/usr/bin/env python3

import collections
import json
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.abuseipdb import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/abuseipdb/settings.py').is_file():
        try:
            from commands.abuseipdb import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        query = params[0].replace('[', '').replace(']', '')
        maxAge = params[1] if len(params)>1 else None
        querytypes = ('ipAddress', 'network')
        try:
            messages = []
            data = None
            if '/' in query:
                ip,netblock = query.split('/')
                url = settings.APIURL['abuseipdb']['url']+'check-block'
                querytype = 'network'
            else:
                ip = query
                url = settings.APIURL['abuseipdb']['url']+'check'
                querytype = 'ipAddress'
            if not re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", ip) and \
               not re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", ip):
                return
            elif querytype in querytypes:
                if not settings.APIURL['abuseipdb']['key']:
                    messages.append({'text': 'Error: the AbuseIPDB module requires a valid API key.'})
                else:
                    headers = {
                        'Accept': 'application/json',
                        'Key': settings.APIURL['abuseipdb']['key'],
                        'Content-Type': settings.CONTENTTYPE,
                    }
                    querystring = {'verbose': True}
                    if querytype == 'network':
                        querystring[querytype] = ip+'/'+netblock
                    if querytype == 'ipAddress':
                        querystring[querytype] = ip
                    if maxAge:
                        querystring['maxAgeInDays'] = maxAge
                    with requests.get(url,headers=headers,params=querystring) as response:
                        json_response = response.json()
                        if 'data' in json_response:
                            reportCategories = {
                                '1': 'DNS compromise',
                                '2': 'DNS poisoning',
                                '3': 'Order fraud',
                                '4': 'DDoS',
                                '5': 'FTP brute-force',
                                '6': 'Ping of death',
                                '7': 'Phishing',
                                '8': 'VoIP fraud',
                                '9': 'Open proxy',
                                '10': 'Web spam',
                                '11': 'Email spam',
                                '12': 'Blog spam',
                                '13': 'VPN',
                                '14': 'Portscan',
                                '15': 'Hacking',
                                '16': 'SQLi',
                                '17': 'Spoofing',
                                '18': 'Brute-force',
                                '19': 'Web bot',
                                '20': 'Infected host',
                                '21': 'Web attack',
                                '22': 'SSH abuse',
                                '23': 'IoT targeted',
                            }
                            data = json_response['data']
                            message = f'**AbuseIPDB lookup for {querystring[querytype]}**'
                            if maxAge:
                                message += f' ({maxAge} days)'
                            message += '\n\n'
                            if querytype == 'ipAddress':
                                fieldmap = collections.OrderedDict({
                                    'ipAddress': 'IP Address',
                                    'hostnames': 'Hostnames',
                                    'usageType': 'Usage',
                                    'isp': 'ISP',
                                    'countryCode': 'Country',
                                    'abuseConfidenceScore': 'Abuse (%)',
                                    'isWhitelisted': 'White-/Blacklisted',
                                    'isTor': 'TOR',
                                    'lastReportedAt': 'Last reported at',
                                    'totalReports': '# Reports',
                                    'reports': 'Reported for',
                                })
                                for field in fieldmap:
                                    if field in data:
                                        message += f'| {fieldmap[field]} '
                                message += '|\n'
                                for field in fieldmap:
                                    if field in data:
                                        if field in ('ipAddress','countryCode','abuseConfidenceScore','isWhitelisted','isTor','totalReports','lastReportedAt'):
                                            message += '| -: '
                                        else:
                                            message += '| :- '
                                message += '|\n'
                                for field in fieldmap:
                                    if field in data:
                                        value = data[field]
                                        if field == 'countryCode':
                                            value = ':flag-'+value.lower()+':'
                                        elif field == 'isTor':
                                            if value:
                                                value = ':onion:'
                                            else:
                                                value = '-'
                                        elif field == 'hostnames':
                                            if len(value)>0:
                                                value = '`'+'`, `'.join(value)+'`'
                                            else:
                                                value = '-'
                                        elif field == 'isWhitelisted':
                                            if value:
                                                value = ':waving_white_flag:'
                                            else:
                                                value = ':waving_black_flag:'
                                        elif field == 'reports':
                                            for report in data[field]:
                                                if 'categories' in report:
                                                    uniquecats = set()
                                                    categories = report['categories']
                                                    for category in categories:
                                                        uniquecats.add(reportCategories[str(category)])
                                            if 'categories' in report:
                                                if len(uniquecats):
                                                    value = '`'+'`, `'.join(uniquecats)+'`'
                                                else:
                                                    value = '-'
                                        else:
                                            if isinstance(value,int) or isinstance(value,float):
                                                value = '`'+str(value)+'`'
                                            elif value:
                                                if len(value):
                                                    value = '`'+value+'`'
                                            else:
                                                value = '`-`'
                                        message += f'| {value} '
                                message += '|\n'
                                message += '\n\n'
                                messages.append({'text': message})
                            if querytype == 'network':
                                fieldmap = collections.OrderedDict({
                                    'networkAddress': 'Netblock',
                                    'numPossibleHosts': '# Hosts',
                                    'addressSpaceDesc': 'Usage',
                                    'reportedAddress': '# Reports',
                                })
                                for field in fieldmap:
                                    if field in data:
                                        message += f'| {fieldmap[field]} '
                                message += '|\n'
                                for field in fieldmap:
                                    if field in data:
                                        if field in ('networkAddress','numPossibleHosts','reports'):
                                            message += '| -: '
                                        else:
                                            message += '| :- '
                                message += '|\n'
                                numreports = 0
                                for field in fieldmap:
                                    if field in data:
                                        value = data[field]
                                        if field == 'reportedAddress':
                                            for report in data[field]:
                                                numreports += report['numReports']
                                            value = '`'+str(numreports)+'`'
                                        else:
                                            if isinstance(value,int) or isinstance(value,float):
                                                value = '`'+str(value)+'`'
                                            elif value:
                                                if len(value):
                                                    value = '`'+value+'`'
                                            else:
                                                value = '`-`'
                                        message += f'| {value} '
                                message += '|\n'
                                message += '\n\n'
                                messages.append({'text': message})
        except Exception as e:
            messages.append({'text': 'A Python error occurred searching the AbuseIPDB API: `%s`\n```%s```\n' % (str(e), traceback.format_exc())})
        finally:
            return {'messages': messages}