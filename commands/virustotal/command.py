#!/usr/bin/env python3

import base64
import json
import random
import re
import requests
from pathlib import Path
try:
    from commands.virustotal import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/virustotal/settings.py').is_file():
        try:
            from commands.virustotal import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params):
    if len(params)>0:
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http')
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'x-apikey': random.choice(settings.APIURL['virustotal']['key']),
        }
        malpedia_headers = {
            'Content-Type': settings.CONTENTTYPE,
            'Authorization': 'apitoken %s' % (settings.APIURL['malpedia']['key'],),
        }
        text = 'VirusTotal search for `%s`:' % (params,)
        # IP report: https://www.virustotal.com/api/v3/ip_addresses/{ip}
        # File report MITRE: https://www.virustotal.com/api/v3/files/{id}/behaviour_mitre_trees
        # URL report: https://www.virustotal.com/api/v3/urls/{id}
        # Domain report: https://www.virustotal.com/api/v3/domains/{domain}
        try:
            querytype = None
            if re.search(r"^[A-Fa-f0-9]{32}$", params) or re.search(r"^[A-Fa-f0-9]{40}$", params) or re.search(r"^[A-Fa-f0-9]{64}$", params):
                querytype = 'file'
                APIENDPOINT = settings.APIURL['virustotal']['url'] + 'files/%s' % (params,)
            elif re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", params):
                querytype = 'ip'
                APIENDPOINT = settings.APIURL['virustotal']['url'] + 'ip_addresses/%s' % (params,)
            elif params.startswith('http'):
                querytype = 'url'
                virustotal_id = base64.urlsafe_b64encode(params.encode()).strip(b'=').decode()
                APIENDPOINT = settings.APIURL['virustotal']['url'] + 'urls/%s' % (virustotal_id,)
            elif re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", params):
                querytype = 'domain'
                APIENDPOINT = settings.APIURL['virustotal']['url'] + 'domains/%s' % (params,)
            if querytype:
                uploads = []
                with requests.get(APIENDPOINT, headers=headers) as response:
                    json_response = response.json()
                    if 'data' in json_response:
                        data = json_response['data']
                        attributes = {}
                        if 'attributes' in data:
                            names = []
                            attributes = data['attributes']
                            if querytype == 'file':
                                if 'bytehero_info' in attributes:
                                    names.append(attributes['bytehero_info'])
                                if 'popular_threat_classification' in attributes:
                                    popular_threat_classification = attributes['popular_threat_classification']
                                    if 'suggested_threat_label' in popular_threat_classification:
                                        names.append(popular_threat_classification['suggested_threat_label'])
                                    if 'popular_threat_name' in popular_threat_classification:
                                        for popular_threat_name in popular_threat_classification['popular_threat_name']:
                                            names.append(popular_threat_name['value'])
                                if len(names)==0:
                                    names = ('Unknown',)
                                text += '\n - Name(s): `' + '`/`'.join(names) + '`'
                                if 'magic' in attributes:
                                    magic = attributes['magic']
                                    text += '\n - Type(s): `' + magic + '`'
                                if 'trid' in attributes:
                                    trid = attributes['trid']
                                    file_type = trid[0]['file_type']
                                    probability = trid[0]['probability']
                                    text += ', `' + file_type + '` (' + str(probability) + '%)'
                                # Attempt to grab YARA data
                                if 'crowdsourced_yara_results' in attributes and settings.APIURL['malpedia']['enabled']:
                                    for crowdsourced_yara_result in attributes['crowdsourced_yara_results']:
                                        if crowdsourced_yara_result['source'] == 'https://malpedia.caad.fkie.fraunhofer.de/':
                                            ruleset_name = crowdsourced_yara_result['ruleset_name'].replace('_auto','')
                                            with requests.get(settings.APIURL['malpedia']['url'] + '/' + ruleset_name + '/zip', headers=malpedia_headers) as response:
                                                if response.content:
                                                    bytes = response.content
                                                    if len(bytes)>0:
                                                        uploads = [{'filename': ruleset_name + '.zip', 'bytes': bytes}]
                                if 'last_analysis_stats' in attributes:
                                    last_analysis_stats = attributes['last_analysis_stats']
                                    count = 0.0
                                    for key in last_analysis_stats:
                                        count += last_analysis_stats[key]
                                    malicious = last_analysis_stats['suspicious'] + last_analysis_stats['malicious']
                                    probability = round(((malicious / count) * 100),2)
                                    if probability>80:
                                        verdict = 'certain'
                                    elif probability>60:
                                        verdict = 'highly likely'
                                    elif probability>20:
                                        verdict = 'probably'
                                    elif probability>0:
                                        verdict = 'possibly'
                                    else:
                                        verdict = 'safe'
                                    text += '\n - Maliciousness: `' + verdict + '` (' + str(probability) + '%)'
                                    with requests.get(APIENDPOINT + '/behaviour_mitre_trees', headers=headers) as response:
                                        json_response = response.json()
                                        mitre_tree_names = ('Malwares', 'Subtechniques', 'Techniques', 'Tools')
                                        if 'data' in json_response:
                                            data = json_response['data']
                                            if 'Zenbox' in data:
                                                Zenbox = data['Zenbox']
                                                if 'tactics' in Zenbox:
                                                    tacticslist = set()
                                                    tactics = Zenbox['tactics']
                                                    for tactic in tactics:
                                                        tacticid = tactic['id']
                                                        tacticname = tactic['name']
                                                        tacticlink = tactic['link']
                                                        tacticslist.add('`' + tacticid + '` [' + tacticname + '](' + tacticlink + ')')
                                                        for mitre_tree in [tree_name.lower() for tree_name in mitre_tree_names]:
                                                            ttplist = set()
                                                            if mitre_tree in tactic:
                                                                for ttp in tactic[mitre_tree]:
                                                                    ttpid = ttp['id']
                                                                    ttpname = ttp['name']
                                                                    ttplink = ttp['link']
                                                                    ttplist.add('`' + ttpid + '` [' + ttpname + '](' + ttplink + ')')
                                                            if len(ttplist)>0:
                                                                text += '\n - TTP(s): ' + ', '.join(ttplist)
                                                    if len(tacticslist)>0:
                                                        text += '\n - Tactic(s): ' + ', '.join(tacticslist)
                            if querytype == 'ip':
                                if 'last_https_certificate' in attributes:
                                    last_https_certificate = attributes['last_https_certificate']
                                    domains = set()
                                    domains.add(last_https_certificate['subject']['CN'])
                                    if 'subject_alternative_name' in last_https_certificate['extensions']:
                                        for domain in last_https_certificate['extensions']['subject_alternative_name']:
                                            domains.add(domain)
                                    algorithm = last_https_certificate['public_key']['algorithm']
                                    if 'key_size' in last_https_certificate['public_key'][algorithm.lower()]:
                                        key_size = last_https_certificate['public_key'][algorithm.lower()]['key_size']
                                    if 'oid' in last_https_certificate['public_key'][algorithm.lower()]:
                                        key_size = last_https_certificate['public_key'][algorithm.lower()]['oid']
                                    signature_algorithm = last_https_certificate['signature_algorithm']
                                    issuers = set()
                                    issuers.add(last_https_certificate['issuer']['O'])
                                    issuers.add(last_https_certificate['issuer']['CN'])
                                    issuers.add(last_https_certificate['issuer']['C'])
                                    issuer = ', '.join(issuers)
                                    text += '\n - Domain Name(s): `' + '`, `'.join(domains) + '`'
                                    text += '\n - Key: `' + algorithm + '-' + str(key_size) + '`, Sig: `' + signature_algorithm + '`, Issuer: `' + issuer + '`'
                                if 'last_analysis_stats' in attributes:
                                    last_analysis_stats = attributes['last_analysis_stats']
                                    count = 0.0
                                    for key in last_analysis_stats:
                                        count += last_analysis_stats[key]
                                    malicious = last_analysis_stats['suspicious'] + last_analysis_stats['malicious']
                                    probability = round(((malicious / count) * 100),2)
                                    if probability>80:
                                        verdict = 'certain'
                                    elif probability>60:
                                        verdict = 'highly likely'
                                    elif probability>20:
                                        verdict = 'potentially'
                                    elif probability>0:
                                        verdict = 'possibly'
                                    else:
                                        verdict = 'safe'
                                    text += '\n - Maliciousness: `' + verdict + '` (' + str(probability) + '%)'
                            if querytype == 'url':
                                if 'last_final_url' in attributes:
                                    last_final_url = attributes['last_final_url']
                                    text += '\n - Final URL: `' + last_final_url + '`'
                                if 'last_http_response_code' in attributes:
                                    last_http_response_code = attributes['last_http_response_code']
                                    text += ' | Status: `' + str(last_http_response_code) + '`'
                                if 'last_http_response_headers' in attributes:
                                    last_http_response_headers = attributes['last_http_response_headers']
                                    if 'Content-Type' in last_http_response_headers:
                                        content_type = last_http_response_headers['Content-Type']
                                        text += ' | Content: `' + content_type + '`'
                                    if 'Content-Length' in last_http_response_headers:
                                        content_length = last_http_response_headers['Content-Length']
                                        text += ' (' + str(content_length) + ' bytes)'
                                    if 'Server' in last_http_response_headers:
                                        server = last_http_response_headers['Server']
                                        text += ' | Server: `' + server + '`'
                                if 'last_analysis_stats' in attributes:
                                    last_analysis_stats = attributes['last_analysis_stats']
                                    count = 0.0
                                    for key in last_analysis_stats:
                                        count += last_analysis_stats[key]
                                    malicious = last_analysis_stats['suspicious'] + last_analysis_stats['malicious']
                                    probability = round(((malicious / count) * 100),2)
                                    if probability>80:
                                        verdict = 'certain'
                                    elif probability>60:
                                        verdict = 'highly likely'
                                    elif probability>20:
                                        verdict = 'potentially'
                                    elif probability>0:
                                        verdict = 'possibly'
                                    else:
                                        verdict = 'safe'
                                    text += '\n - Maliciousness: `' + verdict + '` (' + str(probability) + '%)'
                                if 'threat_names' in attributes:
                                    threat_names = attributes['threat_names']
                                    if len(threat_names)>0:
                                        text += ' | Threat(s): `' + '`, `'.join(threat_names) + '`'
                                if 'tags' in attributes:
                                    tags = attributes['tags']
                                    if len(tags)>0:
                                        text += '(tags: `' + '`, `'.join(attributes['tags']) + '`)'
                            if querytype == 'domain':
                                if 'last_dns_records' in attributes:
                                    text += '\n - DNS Records: '
                                    last_dns_records = attributes['last_dns_records']
                                    dns_record_types = ('A', 'NS', 'MX', 'CNAME', 'TXT')
                                    dns_records = {}
                                    for dns_record_type in dns_record_types:
                                        if not dns_record_type in dns_records:
                                            dns_records[dns_record_type] = set()
                                    for last_dns_record in last_dns_records:
                                        type, value = last_dns_record['type'], last_dns_record['value']
                                        if type in dns_records:
                                            dns_records[type].add(value)
                                    for type in dns_records:
                                        if len(dns_records[type])>0:
                                            text += '**' + type + '**: `' + '`, `'.join(dns_records[type]) + '` | '
                                    text = text[:-2]
                                if 'last_https_certificate' in attributes:
                                    last_https_certificate = attributes['last_https_certificate']
                                    domains = set()
                                    domains.add(last_https_certificate['subject']['CN'])
                                    if 'subject_alternative_name' in last_https_certificate['extensions']:
                                        for domain in last_https_certificate['extensions']['subject_alternative_name']:
                                            domains.add(domain)
                                    algorithm = last_https_certificate['public_key']['algorithm']
                                    if 'key_size' in last_https_certificate['public_key'][algorithm.lower()]:
                                        key_size = last_https_certificate['public_key'][algorithm.lower()]['key_size']
                                    if 'oid' in last_https_certificate['public_key'][algorithm.lower()]:
                                        key_size = last_https_certificate['public_key'][algorithm.lower()]['oid']
                                    signature_algorithm = last_https_certificate['signature_algorithm']
                                    issuers = set()
                                    issuers.add(last_https_certificate['issuer']['O'])
                                    issuers.add(last_https_certificate['issuer']['CN'])
                                    issuers.add(last_https_certificate['issuer']['C'])
                                    issuer = ', '.join(issuers)
                                    text += '\n - Domain Name(s): `' + '`, `'.join(domains) + '`'
                                    text += '\n - Key: `' + algorithm + '-' + str(key_size) + '`, Sig: `' + signature_algorithm + '`, Issuer: `' + issuer + '`'
                                if 'last_analysis_stats' in attributes:
                                    last_analysis_stats = attributes['last_analysis_stats']
                                    count = 0.0
                                    for key in last_analysis_stats:
                                        count += last_analysis_stats[key]
                                    malicious = last_analysis_stats['suspicious'] + last_analysis_stats['malicious']
                                    probability = round(((malicious / count) * 100),2)
                                    if probability>80:
                                        verdict = 'certain'
                                    elif probability>60:
                                        verdict = 'highly likely'
                                    elif probability>20:
                                        verdict = 'potentially'
                                    elif probability>0:
                                        verdict = 'possibly'
                                    else:
                                        verdict = 'safe'
                                    text += '\n - Maliciousness: `' + verdict + '` (' + str(probability) + '%)'
                                if 'threat_names' in attributes:
                                    threat_names = attributes['threat_names']
                                    if len(threat_names)>0:
                                        text += ' | Threat(s): `' + '`, `'.join(threat_names) + '`'
                                if 'tags' in attributes:
                                    tags = attributes['tags']
                                    if len(tags)>0:
                                        text += '(tags: `' + '`, `'.join(attributes['tags']) + '`)'
                        if 'type' in data:
                            type = data['type'].replace('_','-')
                            if querytype == 'url':
                                url = 'https://www.virustotal.com/gui/%s/%s' % (type, virustotal_id)
                            else:
                                url = 'https://www.virustotal.com/gui/%s/%s' % (type, params)
                            text += '\n - VirusTotal detailed report: [%s](%s)' % (params, url)
                        if uploads:
                            return {'messages': [
                                {'text': text},
                                {'text': '\n - Malpedia YARA ruleset(s):', 'uploads': uploads}
                            ]}
                        else:
                            return {'messages': [
                                {'text': text}
                            ]}
                    else:
                        return {'messages': [
                            {'text': 'VirusTotal search for `%s` returned no results.' % (params,)}
                        ]}
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred searching VirusTotal for `%s`:\nError: `%s`' % (params, e)},
            ]}
