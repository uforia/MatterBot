#!/usr/bin/env python3

import collections
import datetime
import re
import requests
import traceback
from pathlib import Path
from ReversingLabs.SDK.a1000 import A1000
try:
    from commands.reversinglabs import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/reversinglabs/settings.py').is_file():
        try:
            from commands.reversinglabs import settings
        except ModuleNotFoundError: # local test run
            import settings

def checkIP(value):
    return True if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", value) or \
        re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$", value) else False

def checkHash(value):
    return True if (checkMD5(value) or checkSHA1(value) or checkSHA256(value) or checkSHA512(value)) else False

def checkHost(value):
    return True if re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", value) else False

def checkURL(value):
    return True if re.search(r"^http(s)?://", value) else False

def checkMD5(value):
    return True if re.search(r"^[A-Fa-f0-9]{32}$", value) else False

def checkSHA1(value):
    return True if re.search(r"^[A-Fa-f0-9]{40}$", value) else False

def checkSHA256(value):
    return True if re.search(r"^[A-Fa-f0-9]{64}$", value) else False

def checkSHA512(value):
    return True if re.search(r"^[A-Fa-f0-9]{128}$", value) else False

def process(command, channel, username, params, files, conn):
    messages = []
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'MatterBot ReversingLabs API integration',
        'Authorization': f"Token {settings.APIURL['a1000']['key']}",
    }
    try:
        querytype = None
        if len(params)>0:
            querytypes = ('ip', 'host', 'url', 'hash')
            querytype = params[0].lower()
            if querytype in querytypes:
                query = params[1].lower()
            else:
                query = params[0].lower()
                if checkIP(querytype):
                    querytype = 'ip'
                    endpoint = 'https://a1000.reversinglabs.com/api/network-threat-intel/ip/'
                elif checkHost(querytype):
                    querytype = 'host'
                    endpoint = 'https://a1000.reversinglabs.com/api/network-threat-intel/domain/'
                elif checkURL(querytype):
                    querytype = 'url'
                    endpoint = 'https://a1000.reversinglabs.com/api/network-threat-intel/url/'
                elif checkHash(querytype):
                    querytype = 'hash'
                    endpoint = 'https://a1000.reversinglabs.com/api/samples/v2/list/details/'
        if querytype:
            if querytype == 'url':
                endpoint += f"?url={query}"
                with requests.get(url=endpoint, headers=headers) as response:
                    if response.status_code in (200,):
                        results = response.json()
                        if 'analysis' in results:
                            analysis = results['analysis']
                            if 'top_threats' in analysis:
                                top_threats = analysis['top_threats']
                                if len(top_threats):
                                    threat_fields = {
                                        'risk_score': 'Risk',
                                        'files_count': 'Count',
                                        'threat_name': 'Name',
                                    }
                                    
                                    first_analysis = analysis['first_analysis'] if 'first_analysis' in analysis else None
                                    message = f"**ReversingLabs URL Analysis**: `{query}`"
                                    if first_analysis:
                                        message += f"**First Seen**: `{first_analysis}`"
                                    message += "\n\n"
                                    for threat_field in threat_fields:
                                        message += f"| **{threat_fields[threat_field]}** "
                                    message += "|\n"
                                    for threat_field in threat_fields:
                                        message += f"| :- "
                                    message += "|\n"
                                    for top_threat in top_threats:
                                        for threat_field in threat_fields:
                                            message += f"| `{top_threat[threat_field]}` "
                                        message += "|\n"
                                    message += "\n\n"
                                    messages.append({'text': message})
                        if 'third_party_reputations' in results:
                            if 'statistics' in results['third_party_reputations']:
                                message = f"| **ReversingLabs Third Party Results** | **Query**: `{query}` |\n"
                                message += '| :- | :- |\n'
                                malicious = results['third_party_reputations']['statistics']['malicious']
                                suspicious = results['third_party_reputations']['statistics']['suspicious']
                                clean = results['third_party_reputations']['statistics']['clean']
                                undetected = results['third_party_reputations']['statistics']['undetected']
                                total = results['third_party_reputations']['statistics']['total']
                                message += f"| **Statistics** | Total: `{total}` |\n"
                                message += f"| **Undetected** | `{undetected}` |\n"
                                message += f"| **Clean** | `{clean}` |\n"
                                message += f"| **Suspicious** | `{suspicious}` |\n"
                                message += f"| **Malicious** | `{malicious}` |\n"
                                message += "\n\n"
                                messages.append({'text': message})
                        if 'classification' in results:
                            classification = results['classification']
                            message = f"**ReversingLabs Classification:** `{classification}`"
                            if 'threat_level' in results:
                                threat_level = results['threat_level']
                                message += f" **Threat Level**: `{threat_level}`"
                            if 'reason' in results:
                                reason = results['reason'].replace('_', ' ').title()
                                message += f" **Reason**: `{reason}`"
                            messages.append({'text': message})
            if querytype == 'host':
                endpoint += f"{query}/"
                with requests.get(url=endpoint, headers=headers) as response:
                    if response.status_code in (200,):
                        results = response.json()
                        print(results)
                        if 'top_threats' in results:
                            top_threats = results['top_threats']
                            if len(top_threats):
                                threat_fields = {
                                    'risk_score': 'Risk',
                                    'files_count': 'Count',
                                    'threat_name': 'Name',
                                }
                                message = f"**ReversingLabs Top Threats**: `{query}`\n\n"
                                for threat_field in threat_fields:
                                    message += f"| **{threat_fields[threat_field]}** "
                                message += "|\n"
                                for threat_field in threat_fields:
                                    message += f"| :- "
                                message += "|\n"
                                for top_threat in top_threats:
                                    for threat_field in threat_fields:
                                        message += f"| `{top_threat[threat_field]}` "
                                    message += "|\n"
                                message += "\n\n"
                                messages.append({'text': message})
                        if 'third_party_reputations' in results:
                            if 'statistics' in results['third_party_reputations']:
                                message = f"| **ReversingLabs Third Party Results** | **Query**: `{query}` |\n"
                                message += '| :- | :- |\n'
                                malicious = results['third_party_reputations']['statistics']['malicious']
                                suspicious = results['third_party_reputations']['statistics']['suspicious']
                                clean = results['third_party_reputations']['statistics']['clean']
                                undetected = results['third_party_reputations']['statistics']['undetected']
                                total = results['third_party_reputations']['statistics']['total']
                                message += f"| **Statistics** | Total: `{total}` |\n"
                                message += f"| **Undetected** | `{undetected}` |\n"
                                message += f"| **Clean** | `{clean}` |\n"
                                message += f"| **Suspicious** | `{suspicious}` |\n"
                                message += f"| **Malicious** | `{malicious}` |\n"
                                message += "\n\n"
                                messages.append({'text': message})
                        if 'last_dns_records' in results:
                            last_dns_records = results['last_dns_records']
                            message = f"**ReversingLabs DNS Results**: `{query}`\n\n"
                            message += f"| **Type** | **Value** | **Resolver** |\n"
                            message += '| :- | :- | :- |\n'
                            for last_dns_record in last_dns_records:
                                message += f"| {last_dns_record['type']} | {last_dns_record['value']} | {last_dns_record['provider']} |\n"
                            message += '\n\n'
                            messages.append({'text': message})
                        if 'last_dns_records_time' in results:
                            messages.append({'text': f"**Last ReversingLabs DNS record resolution:** `{results['last_dns_records_time']}`\n"})
            if querytype == 'ip':
                endpoint += f"{query}/report/"
                with requests.get(url=endpoint, headers=headers) as response:
                    if response.status_code in (200,):
                        results = response.json()
                        if 'top_threats' in results:
                            top_threats = results['top_threats']
                            if len(top_threats):
                                threat_fields = {
                                    'risk_score': 'Risk',
                                    'files_count': 'Count',
                                    'threat_name': 'Name',
                                }
                                message = f"**ReversingLabs Top Threats**: `{query}`\n\n"
                                for threat_field in threat_fields:
                                    message += f"| **{threat_fields[threat_field]}** "
                                message += "|\n"
                                for threat_field in threat_fields:
                                    message += f"| :- "
                                message += "|\n"
                                for top_threat in top_threats:
                                    for threat_field in threat_fields:
                                        message += f"| `{top_threat[threat_field]}` "
                                    message += "|\n"
                                message += "\n\n"
                                messages.append({'text': message})
                        if 'third_party_reputations' in results:
                            if 'statistics' in results['third_party_reputations']:
                                message = f"| **ReversingLabs Third Party Results** | **Query**: `{query}` |\n"
                                message += '| :- | :- |\n'
                                malicious = results['third_party_reputations']['statistics']['malicious']
                                suspicious = results['third_party_reputations']['statistics']['suspicious']
                                clean = results['third_party_reputations']['statistics']['clean']
                                undetected = results['third_party_reputations']['statistics']['undetected']
                                total = results['third_party_reputations']['statistics']['total']
                                message += f"| **Statistics** | Total: `{total}` |\n"
                                message += f"| Undetected | `{undetected}` |\n"
                                message += f"| Clean | `{clean}` |\n"
                                message += f"| Suspicious | `{suspicious}` |\n"
                                message += f"| Malicious | `{malicious}` |\n"
                                message += "\n\n"
                                messages.append({'text': message})
                        if 'modified_time' in results:
                            messages.append({'text': f"**Last updated:** `{results['modified_time']}`\n"})
            if querytype == 'hash':
                ticloudfields = collections.OrderedDict({
                    'classification': 'Classification',
                    'first_seen': 'Timestamp',
                    'classification_result': 'Name',
                })
                ticorehashfields = collections.OrderedDict({
                    'md5': 'MD5',
                    'rha0': 'RHA0',
                    'sha1': 'SHA1',
                    'sha256': 'SHA256',
                    'sha512': 'SHA512',
                    'ssdeep': 'SSDEEP',
                    'tlsh': 'TLSH',
                })
                data = {
                    'hash_values': [f"{query}",],
                    'include_networkthreatintelligence': True,
                    'skip_reanalysis': True,
                }
                with requests.post(url=endpoint, headers=headers, json=data) as response:
                    results = response.json()
                    if 'count' in results:
                        if results['count']>0:
                            samplehashes = []
                            uploads = []
                            results = results['results']
                            for result in results:
                                message = f"| **ReversingLabs Results Summary** | **Query**: `{query}` |\n"
                                message += '| :- | :- |\n'
                                if 'ticloud' in result:
                                    for ticloudfield in ticloudfields:
                                        if ticloudfield in result['ticloud']:
                                            value = result['ticloud'][ticloudfield]
                                            if ticloudfield == 'classification':
                                                value += f" ({result['ticloud']['riskscore']})"
                                        message += f"| **{ticloudfields[ticloudfield]}** | `{value}` |\n"
                                if 'ticore' in result:
                                    if 'info' in result['ticore']:
                                        if 'file' in result['ticore']['info']:
                                            if 'size' in result['ticore']['info']['file']:
                                                message += f"| **Filesize** | `{result['ticore']['info']['file']['size']}` |\n"
                                                if 'hashes' in result['ticore']['info']['file']:
                                                    for hashset in result['ticore']['info']['file']['hashes']:
                                                        if 'name' in hashset:
                                                            if hashset['name'] in ticorehashfields:
                                                                name = ticorehashfields[hashset['name']]
                                                                value = hashset['value']
                                                                if name.lower() in ('sha256',):
                                                                    samplehashes.append(value)
                                                                message += f"| **{name}** | `{value}` |\n"
                                message += '\n\n'
                                messages.append({'text': message})
                                for samplehash in samplehashes:
                                    endpoint = f"https://a1000.reversinglabs.com/api/samples/{samplehash}/download/"
                                    with requests.get(url=endpoint, headers=headers) as sample:
                                        if response.status_code in (200,):
                                            uploads.append({'filename': f"sample-{samplehash}.bin", 'bytes': sample.content})
                            uploads.append({'filename': 'reversingslabs-'+query+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content})
                            messages.append({'text': 'ReversingLabs JSON output and related samples:', 'uploads': uploads})
        else:
            messages.append({'text': f"ReversingLabs module does not understand type/query: {query}"})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching the ReversingLabs API: `%s`\n```%s```\n' % (str(e), traceback.format_exc())})
    finally:
        return {'messages': messages}