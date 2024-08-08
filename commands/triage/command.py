#!/usr/bin/env python3

import collections
import datetime
import json
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.triage import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/triage/settings.py').is_file():
        try:
            from commands.triage import settings
        except ModuleNotFoundError: # local test run
            import settings

def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    messages = []
    stripchars = '`\\[\\]\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    try:
        if not settings.APIURL['triage']['key']:
            messages.append({'text': 'Tria.ge: No API key defined ...'})
        else:
            if len(params)>0:
                querytype = None
                query = ''.join(' '.join(params).split('query:')[1:]).split('filter')[0].strip()
                filters = ''.join(' '.join(params).split('filter:')[1:]).split('query')[0].replace(' ','+')
                if query:
                    if re.search(r"^[0-9]{6}-[a-zA-Z0-9]{10}$",query):
                        querytype = 'sample'
                    elif re.search(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$", query):
                        querytype = 'ip'
                    elif re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$", query):
                        querytype = 'ip'
                    elif re.search(r"^0x[a-fA-F0-9]{40}$", query) or \
                        re.search(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$", query) or \
                        re.search(r"^X[1-9A-HJ-NP-Za-km-z]{33}$", query) or \
                        re.search(r"^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$", query):
                        querytype = 'wallet'
                    elif re.search(r"^[A-Fa-f0-9]{32}$", query):
                        querytype = 'md5'
                    elif re.search(r"^[A-Fa-f0-9]{40}$", query):
                        querytype = 'sha1'
                    elif re.search(r"^[A-Fa-f0-9]{64}$", query):
                        querytype = 'sha256'
                    elif re.search(r"^[A-Fa-f0-9]{128}$", query):
                        querytype = 'sha512'
                    elif 'http' in query:
                        querytype = 'url'
                        query = re.sub(r'http(s)?://', '', query)
                    elif is_valid_hostname(query):
                        querytype = 'domain'
                APIENDPOINT = settings.APIURL['triage']['url']
                if querytype and query:
                    if querytype in ('sample',):
                        APIENDPOINT = APIENDPOINT.strip('/')+'/samples/%s/overview.json' % (query,)
                    else:
                        APIENDPOINT = APIENDPOINT.strip('/')+'/search?query=%s:%s' % (querytype,query)
                if len(filters):
                    if querytype and query:
                        APIENDPOINT += '+and+%s' % (filters,)
                    else:
                        APIENDPOINT = APIENDPOINT.strip('/')+'/search?query=%s' % (filters,)
                if APIENDPOINT:
                    if not querytype in ('sample',):
                        APIENDPOINT+='&limit=%d' % (settings.APIURL['triage']['apilimit'],)
                    headers = {
                        'User-Agent': 'Tria.ge Python MatterBot v0.1',
                        'Content-Type': '%s' % (settings.CONTENTTYPE,),
                        'Authorization': 'Bearer %s' % (settings.APIURL['triage']['key'],),
                    }
                    offset = None
                    count = 0
                    results = {}
                    while True:
                        if offset:
                            APIENDPOINTOFFSET = APIENDPOINT+'&offset=%s' % (offset,)
                        else:
                            APIENDPOINTOFFSET = APIENDPOINT
                        with requests.get(APIENDPOINTOFFSET, headers=headers) as response:
                            if not response.status_code == 200:
                                try:
                                    json_response = response.json()
                                    if 'error' in json_response:
                                        error_message = json_response['message'].lower()
                                        messages.append({'text': 'Tria.ge API error: `%s`.' % (error_message, )})
                                        break
                                except:
                                    messages.append({'text': 'Unknown Tria.ge API error: perhaps the query was invalid or the API errored out.'})
                                    break
                            else:
                                json_response = response.json()
                                if 'data' in json_response:
                                    data = json_response['data']
                                    if len(data):
                                        count += len(data)
                                        for result in data:
                                            id = result['id']
                                            if not id in results:
                                                results[id] = result
                                        if count > settings.APIURL['triage']['limit']:
                                            break
                                else:
                                    if not querytype in ('sample',):
                                        messages.append({'text': 'An error occurred searching Tria.ge. Perhaps the query was invalid or the API errored out.'})
                                        messages.append({'text': 'Raw API response: `%s`' % (response.content,)})
                                        break
                                    else:
                                        id = json_response['sample']
                                        results = json_response
                                if 'next' in json_response:
                                    if 'data' in json_response:
                                        data = json_response['data']
                                        if len(data) >= settings.APIURL['triage']['apilimit']:
                                            next = json_response['next']
                                            if next:
                                                offset = next
                                        else:
                                            break
                                else:
                                    break
                    if len(results):
                        printcount = 1
                        header = '** Tria.ge API search for'
                        if querytype and query:
                            header += ' type: `%s`, value: `%s`' % (querytype,query)
                        if filters:
                            header += ' filters: `%s`' % (filters.replace('+',' '),)
                        header += '**\n\n'
                        if not querytype in ('sample',):
                            message = header
                            fields = collections.OrderedDict({
                                'id': 'Triage ID',
                                'sample': 'Triage ID', 
                                'created': 'Timestamp',
                                'submitted': 'Timestamp',
                                'kind': 'Type',
                                'domain': 'Host',
                                'filename': 'Filename',
                                'target': 'Target',
                                'tags': 'TTPs',
                                'url': 'URL',
                                'md5': 'MD5',
                                'sha1': 'SHA1',
                                'sha256': 'SHA256',
                                'sha512': 'SHA512',
                            })
                            resultstruct = results[list(results)[0]]
                            message += '| **#** '
                            for field in fields:
                                if field in resultstruct:
                                    message += '| **%s** ' % (fields[field],)
                            message += '|\n'
                            message += '| -: '
                            for field in fields:
                                if field in resultstruct:
                                    message += '| :- '
                            message += '|\n'
                            for result in results:
                                message += '| `%d` ' % (printcount,)
                                printcount += 1
                                for field in fields:
                                    if field in resultstruct:
                                        message += '| `%s` ' % (results[result][field],)
                                message += '|\n'
                                if printcount > 10:
                                    break
                            message += '\n\n'
                            messages.append({'text': message})
                            if printcount > 10:
                                messages.append({'text': 'Maximum number of displayed results limited to 10; check the JSON attachment for %d results.' % (len(results),)})
                                if querytype:
                                    messages.append({'text': 'Tria.ge JSON output:', 'uploads': [
                                                        {'filename': 'triage-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': json.dumps(results, indent=4)}
                                                    ]})
                                else:
                                    messages.append({'text': 'Tria.ge JSON output:', 'uploads': [
                                                        {'filename': 'triage-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': json.dumps(results, indent=4)}
                                                    ]})
                        else:
                            for samplesection in results:
                                message = ''
                                if samplesection in ('sample',):
                                    fields = collections.OrderedDict({
                                        'id': 'Triage ID',
                                        'created': 'Timestamp',
                                        'score': 'Score',
                                        'size': 'Filesize',
                                        'md5': 'MD5',
                                        'sha1': 'SHA1',
                                        'sha256': 'SHA256',
                                        'sha512': 'SHA512',
                                        'ssdeep': 'SSDEEP',
                                    })
                                    sampleinfo = results[samplesection]
                                    message += '| **Type** | **Value **|\n'
                                    message += '| :- | :- |\n'
                                    for field in fields:
                                        value = '-'
                                        if field in sampleinfo:
                                            if field in ('score',):
                                                score = sampleinfo[field]
                                                if not score:
                                                    scoretext = 'N/A'
                                                elif score == 1:
                                                    scoretext = 'No (potentially) malicious behavior was detected'
                                                elif score >= 2 and score <= 5:
                                                    scoretext = 'Likely benign'
                                                elif score >= 6 and score <= 7:
                                                    scoretext = 'Shows suspicious behavior'
                                                elif score >= 8 and score <= 9:
                                                    scoretext = 'Likely malicious'
                                                elif score == 10:
                                                    scoretext = 'Known bad'
                                                value = scoretext
                                            else:
                                                value = sampleinfo[field]
                                        message += '| **%s** | `%s` |\n' % (fields[field], value)
                                    message += '\n\n'
                                    messages.append({'text': header + message})
                                if samplesection in ('signatures',):
                                    ttpset = {}
                                    behaviourset = set()
                                    for signature in results[samplesection]:
                                        ttpname = signature['name']
                                        if not ttpname in behaviourset:
                                            if 'ttp' in signature:
                                                ttps = signature['ttp']
                                                for ttp in ttps:
                                                    if not ttp in ttpset:
                                                        ttpset[ttp] = ttpname
                                            else:
                                                behaviourset.add(ttpname)
                                    message += '| **MITRE ID** | **Behaviour** |\n'
                                    message += '| -: | :- |\n'
                                    for ttp in sorted(ttpset):
                                        message += '| %s | %s |\n' % (ttp, ttpset[ttp])
                                    for behaviour in sorted(behaviourset):
                                        message += '| - | %s |\n' % (behaviour,)
                                    message += '|\n'
                                    message += '\n**Easy TTP list for further pivoting:** `%s`' % (' '.join(sorted(ttpset.keys())),)
                                    messages.append({'text': message})
                                if samplesection in ('targets',):
                                    for target in results[samplesection]:
                                        ioctypes = {
                                            'domains': 'Domains',
                                            'ips': 'IPs',
                                            'urls': 'URLs',
                                        }
                                        iocs = {}
                                        if 'iocs' in target:
                                            for ioctype in target['iocs']:
                                                if ioctype in ioctypes:
                                                    for ioc in target['iocs'][ioctype]:
                                                        if not ioctype in iocs:
                                                            iocs[ioctype] = []
                                                        if not ioc in iocs[ioctype]:
                                                            iocs[ioctype].append(ioc.replace('http','hxxp').replace('.','[.]',1))
                                    message += '| **Type** | **Value** |\n'
                                    message += '| -: | :- |\n'
                                    for ioctype in iocs:
                                        message += '| %s | `%s` |\n' % (ioctypes[ioctype], '` `'.join(sorted(iocs[ioctype])))
                                    message += '|\n'
                                    messages.append({'text': message})
                            APIENDPOINT = APIENDPOINT = settings.APIURL['triage']['url'].strip('/')+'/samples/%s/sample' % (query,)
                            with requests.get(APIENDPOINT, headers=headers) as response:
                                if response.status_code == 200:
                                    messages.append({'text': 'Tria.ge Malware Sample (DANGEROUS):', 'uploads': [
                                                        {'filename': 'triage-'+querytype+'-'+query+'.bin', 'bytes': response.content}
                                                    ]})                            
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching Tria.ge: %s\n%s' % (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
