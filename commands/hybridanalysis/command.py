#!/usr/bin/env python3

import datetime
import re
import requests
from pathlib import Path
try:
    from commands.hybridanalysis import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/hybridanalysis/settings.py').is_file():
        try:
            from commands.hybridanalysis import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params):
    # Methods to query the current API account info (credits etc.)
    messages = []
    querytypes = ['IPv4','IPv6','hostname','md5','sha1','sha256','url']
    stripchars = '`\[\]\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    try:
        if len(params)>0:
            query = regex.sub('',params[0].lower())
            querytype = None
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", query):
                endpoint = 'search/terms'
                querytype = 'host'
            elif re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", query):
                endpoint = 'search/terms'
                querytype = 'host'
            elif re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", query):
                endpoint = 'search/terms'
                querytype = 'domain'
            elif 'http' in query:
                endpoint = 'search/terms'
                querytype = 'url'
            elif re.search(r"^[A-Fa-f0-9]{32}$", query):
                endpoint = 'search/hash'
                querytype = 'hash'
            elif re.search(r"^[A-Fa-f0-9]{40}$", query):
                endpoint = 'search/hash'
                querytype = 'hash'
            elif re.search(r"^[A-Fa-f0-9]{64}$", query):
                endpoint = 'search/hash'
                querytype = 'hash'
            elif re.search(r"((\d*):(\w*):(\w*)|(\d*):(\w*)\+(\w*):(\w*))", query):
                endpoint = 'search/terms'
                querytype = 'ssdeep'
            else:
                endpoint = 'search/terms'
                querytype = 'vx-family'
            if querytype:
                headers = {
                    'User-Agent': 'VxApi CLI Connector',
                    'api-key': '%s' % settings.APIURL['hybridanalysis']['key'],
                }
                data = {querytype:query}
                APIENDPOINT = settings.APIURL['hybridanalysis']['url']+endpoint
                with requests.post(APIENDPOINT, data=data, headers=headers) as response:
                    message = ''
                    json_response = response.json()
                    if len(json_response):
                        count = 0
                        # Deal with /search/hash output
                        if endpoint == 'search/hash':
                            for entry in json_response:
                                count += 1
                                message = '| Hybrid-Analysis Result %s | `%s` |' % (count,query)
                                message += '\n| -: | :- |'
                                singlefields = {
                                    'submit_name': 'Filename',
                                    'verdict': 'Verdict',
                                    'analysis_start_time': 'Submitted at',
                                    'type': 'Filetype',
                                    'size': 'Filesize',
                                    'md5': 'MD5 hash',
                                    'sha1': 'SHA1 hash',
                                    'sha256': 'SHA256 hash',
                                    'ssdeep': 'SSDEEP hash',
                                    'imphash': 'Imphash',
                                    'vx_family': 'Malware family',
                                }
                                multifields = {
                                    'tags': 'Tags',
                                    'classification_tags': 'Classifications',
                                    'domains': 'Domains',
                                    'compromised_hosts': 'Compromised hosts',
                                    'hosts': 'Hosts',
                                    'extracted_files': 'Extracted files',
                                    'processes': 'Processes',
                                    'mitre_attcks': 'MITRE ATT&CK TTPs',
                                    'signatures': 'Signatures',
                                }
                                for singlefield in singlefields:
                                    if singlefield in entry:
                                        value = entry[singlefield]
                                        if value:
                                            message += '\n| %s | `%s` |' % (singlefields[singlefield], entry[singlefield])
                                for multifield in multifields:
                                    if multifield in entry:
                                        value = entry[multifield]
                                        if value:
                                            message += '\n| %s | `%s` |' % (multifields[multifield], '`, `'.join(entry[multifield]))
                                message += '\n\n'
                                messages.append({'text': message})
                        # Deal with /search/terms output
                        if endpoint == 'search/terms':
                            if 'result' in json_response:
                                for entry in json_response['result']:
                                    count += 1
                                    # Only display the first five results for now
                                    if count>3:
                                        messages.append({
                                            'text': 'More than 3 results, attaching complete JSON.',
                                            'uploads': [
                                                {'filename': 'hybridanalysis-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content}
                                            ]
                                            })
                                        break
                                    message = '| Hybrid-Analysis Result %s | `%s` |' % (count,query)
                                    message += '\n| -: | :- |'
                                    singlefields = {
                                        'submit_name': 'Submitted Name',
                                        'verdict': 'Verdict',
                                        'analysis_start_time': 'Submitted at',
                                        'vx_family': 'Malware family',
                                    }
                                    for singlefield in singlefields:
                                        if singlefield in entry:
                                            value = entry[singlefield]
                                            if value:
                                                message += '\n| %s | `%s` |' % (singlefields[singlefield], entry[singlefield])
                                    message += '\n\n'
                                    messages.append({'text': message})

    except Exception as e:
        messages.append({'text': 'A Python error occurred searching Hybrid-Analysis:\nError:' + str(e)})
    finally:
        return {'messages': messages}
