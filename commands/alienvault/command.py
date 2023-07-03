#!/usr/bin/env python3

import datetime
import math
import random
import re
import requests
import urllib
from pathlib import Path
try:
    from commands.alienvault import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/alienvault/settings.py').is_file():
        try:
            from commands.alienvault import settings
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
                querytype = 'IPv4'
            elif re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", query):
                querytype = 'IPv6'
            elif re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", query):
                querytype = 'hostname'
            elif re.search(r"^[A-Fa-f0-9]{32}$", query):
                querytype = 'md5'
            elif re.search(r"^[A-Fa-f0-9]{40}$", query):
                querytype = 'sha1'
            elif re.search(r"^[A-Fa-f0-9]{64}$", query):
                querytype = 'sha256'
            elif 'http' in query:
                querytype = 'url'
            if querytype:
                headers = {
                    'Accept-Encoding': settings.CONTENTTYPE,
                    'Content-Type': settings.CONTENTTYPE,
                    'X-OTX-API-KEY': '%s' % settings.APIURL['alienvault']['key'],
                }
                if querytype in ('IPv4','IPv6'):
                    endpoints = (querytype+'/'+query+'/reputation',
                                 querytype+'/'+query+'/geo',
                                 querytype+'/'+query+'/malware',
                                 querytype+'/'+query+'/url_list',
                                 querytype+'/'+query+'/passive_dns')
                if querytype in ('hostname','domain'):
                    endpoints = ('hostname/'+query+'/geo',
                                 'hostname/'+query+'/malware',
                                 'hostname/'+query+'/url_list',
                                 'hostname/'+query+'/passive_dns',
                                 'domain/'+query+'/malware',
                                 'domain/'+query+'/url_list')
                if querytype in ('md5','sha1','sha256'):
                    endpoints = ('file/'+query+'/analysis',)
                if querytype in ('url'):
                    endpoints = ('url/'+query+'/url_list',)
                for endpoint in endpoints:
                    APIENDPOINT = settings.APIURL['alienvault']['url']+endpoint+'?limit=10'
                    with requests.get(APIENDPOINT, headers=headers) as response:
                        message = ''
                        json_response = response.json()
                        geofields = {
                            'asn': 'ASN',
                            'city': 'City',
                            'region': 'Region',
                            'country_name': 'Country',
                        }
                        for field in geofields:
                            if field in json_response:
                                value = json_response[field]
                                message += '\n| **%s** | `%s` |' % (geofields[field], value)
                        if 'data' in json_response:
                            for entry in json_response['data']:
                                if 'hash' in entry and 'detections' in entry:
                                    detections = set()
                                    for detection in entry['detections']:
                                        if entry['detections'][detection]:
                                            detections.add(entry['detections'][detection])
                                    message += '\n| **Hash**: `%s` | `%s` |' % (entry['hash'], '`, `'.join(sorted(detections)))
                        if 'url_list' in json_response:
                            urls = set()
                            for entry in json_response['url_list']:
                                url = entry['url']
                                urls.add(url)
                            if len(urls):
                                message += '\n| **Associated URLs** | `%s` |' % ('`, `'.join(sorted(urls)))
                        if 'passive_dns' in json_response:
                            hostnames = set()
                            for entry in json_response['passive_dns']:
                                hostname = entry['hostname']
                                hostnames.add(hostname)
                                if len(hostnames)>20:
                                    break
                            if len(hostnames):
                                message += '\n| **Passive DNS**'
                                if len(hostnames)>10:
                                    message += ' (*Note: only 20 entries shown*)'
                                message += ' | `%s` |' % ('`, `'.join(sorted(hostnames)))
                        if 'analysis' in json_response:
                            if 'plugins' in json_response['analysis']:
                                if 'exiftool' in json_response['analysis']['plugins']:
                                    exiftoolfields = {
                                        'Original_Filename': 'Filename',
                                        'File_Description': 'Description',
                                        'MIME_Type': 'MIME-type'
                                    }
                                    for field in exiftoolfields:
                                        if field in json_response['analysis']['plugins']['exiftool']['results']:
                                            value = json_response['analysis']['plugins']['exiftool']['results'][field]
                                            if len(value):
                                                message += '\n| **%s** | `%s` |' % (exiftoolfields[field], value)
                            if 'info' in json_response['analysis']:
                                if 'results' in json_response['analysis']['info']:
                                    infofields = {
                                        'file_type': 'File type',
                                        'filesize': 'Filesize',
                                        'md5': 'MD5 hash',
                                        'sha1': 'SHA1 hash',
                                        'sha256': 'SHA256 hash',
                                        'ssdeep': 'SSDEEP hash'
                                    }
                                    for field in infofields:
                                        if field in json_response['analysis']['info']['results']:
                                            value = json_response['analysis']['info']['results'][field]
                                            if len(value):
                                                message += '\n| **%s** | `%s` |' % (infofields[field], value)
                            if 'plugins' in json_response['analysis']:
                                if 'cuckoo' in json_response['analysis']['plugins']:
                                    for signature in json_response['analysis']['plugins']['cuckoo']['result']['signatures']:
                                        if signature['name'] == 'antivirus_virustotal':
                                            detections = set()
                                            families = set()
                                            for detection in signature['data']:
                                                for k in detection:
                                                    detections.add(detection[k])
                                            for family in signature['families']:
                                                for k in family:
                                                    families.add(family[k])
                                            if len(detections):
                                                message += '\n| **Detections** | `%s` |' % '`, `'.join(sorted(detections))
                                            if len(families):
                                                message += '\n| **Families** | `%s` |' % '`, `'.join(sorted(families))
                        if len(message):
                            table = '| **AlienVault %s Lookup** | **Value(s)** |\n| -: | :- |'+message+'\n\n' % (querytype,)
                            messages.append({'text': table})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching AlienVault OTX:\nError:' + str(e)})
    finally:
        return {'messages': messages}