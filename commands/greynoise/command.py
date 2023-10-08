#!/usr/bin/env python3

import datetime
import math
import random
import re
import requests
import traceback
import urllib.parse
from pathlib import Path
try:
    from commands.greynoise import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/greynoise/settings.py').is_file():
        try:
            from commands.greynoise import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(settings.APIURL['greynoise']['key']):
        apikey = random.choice(settings.APIURL['greynoise']['key'])
    else:
        return
    # Methods to query the current API account info (credits etc.)
    querytypes = {
        'community':    '/v3/community/',
        'ipcontext':    '/v2/noise/context/',
        'ipquick':      '/v2/noise/quick/',
        'riot':         '/v2/riot/',
        'gnql':         '/v2/experimental/gnql',
        'gnqlstats':    '/v2/experimental/gnql/stats',
        'timeline':     '/v3/noise/ips/',
        'similarity':   '/v3/similarity/ips/',
        'ping':         '/ping',
    }
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    try:
        if len(params)>0:
            querytype = params[0] if params[0] in querytypes else 'community'
            if not querytype in querytypes:
                return
            APIENDPOINT = settings.APIURL['greynoise']['url']
            headers = {
                'accept':   settings.CONTENTTYPE,
                'key':      apikey,
            }
            if querytype == 'ping':
                APIENDPOINT += querytypes[querytype]
                with requests.get(APIENDPOINT, headers=headers) as response:
                    json_response = response.json()
                    if 'message' in json_response:
                        if json_response['message'] == 'pong':
                            expiration = json_response['expiration']
                            offering = json_response['offering']
                            message =  '\n| **GreyNoise** | `Account Information` |'
                            message += '\n| :- | -: |'
                            message += '\n| **Offering** | `%s` |' % (offering,)
                            message += '\n| **Expiration** | `%s` |' % (expiration,)
                            message += '\n\n'
                            messages.append({'text': message})
            else:
                if len(params)>1:
                    query = params[1:]
                else:
                    query = params[0].strip()
                    if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", query) or \
                       re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", query):
                        querytype = 'community'
                if len(query):
                    if querytype == 'community':
                        query = query[0].strip()
                        APIENDPOINT += urllib.parse.quote(querytypes[querytype]+'%s' % (query,))
                        with requests.get(APIENDPOINT, headers=headers) as response:
                            json_response = response.json()
                            if response.status_code in (200,404):
                                message =  '\n| **GreyNoise** Lookup Type | `%s` |' % (querytype)
                                message += '\n| :- | -: |'
                                fields = {
                                    'ip': 'IP Address',
                                    'noise': 'Noise',
                                    'riot': 'RIOT',
                                    'message': 'Context',
                                }
                                for field in fields:
                                    if field in json_response:
                                        message += '\n| **%s** | `%s` |' % (fields[field],json_response[field])
                                message += '\n\n'
                                messages.append({'text': message})
                    if querytype == 'ipcontext':
                        query = query[0].strip()
                        APIENDPOINT += urllib.parse.quote(querytypes[querytype]+'%s' % (query,))
                        with requests.get(APIENDPOINT, headers=headers) as response:
                            json_response = response.json()
                            if response.status_code == 200:
                                message =  '\n| **GreyNoise** Lookup Type | `%s` |' % (querytype)
                                message += '\n| :- | :- |'
                                fields = {
                                    'ip': 'IP Address',
                                    'first_seen': 'First Seen',
                                    'last_seen': 'Last Seen',
                                    'seen': 'Seen',
                                    'tags': 'Behaviour',
                                    'actor': 'Actor',
                                    'spoofable': 'Spoofable',
                                    'classification': 'Classification',
                                    'bot': 'Is this a bot?',
                                    'vpn': 'Is this a VPN exit node?',
                                    'vpn_service': 'VPN Service',
                                    'metadata': 'Metadata',
                                    'raw_data': 'Miscellaneous',
                                }
                                for field in fields:
                                    if field in json_response:
                                        if field == 'tags':
                                            value = '`, `'.join(json_response['tags'])
                                        elif field == 'metadata':
                                            metadatafields = {
                                                'tor': 'Is this a TOR exit node?',
                                                'asn': 'ASN',
                                                'rdns': 'Reverse DNS',
                                                'os': 'Operating System',
                                                'source_country_code': 'Origin Country',
                                                'destination_country_codes': 'Target Countries',
                                            }
                                            for metadatafield in metadatafields:
                                                if metadatafield in json_response[field]:
                                                    if metadatafield == 'source_country_code':
                                                        metadatavalue = ':flag-'+json_response[field][metadatafield].lower()+':'
                                                    elif metadatafield == 'destination_country_codes':
                                                        countries = []
                                                        for country_code in json_response[field][metadatafield]:
                                                            countries.append(':flag-'+country_code.lower()+':')
                                                        metadatavalue = ' '.join(sorted(countries))
                                                        metadatavalue = metadatavalue.strip()
                                                    elif metadatafield == 'tor':
                                                        metadatavalue = json_response[field][metadatafield]
                                                        if metadatavalue == True:
                                                            metadatavalue = '`Yes`'
                                                        elif metadatavalue == False:
                                                            metadatavalue = '`No`'
                                                        else:
                                                            metadatavalue = ''
                                                    else:
                                                        metadatavalue = '`'+str(json_response[field][metadatafield])+'`'
                                                    if len(metadatavalue)>2:
                                                        message += '\n| **%s** | %s |' % (metadatafields[metadatafield],metadatavalue)
                                        elif field == 'raw_data':
                                            rawdatafields = {
                                                'scan': 'Ports Scanned',
                                                'web': 'Web Paths Scanned',
                                                'ja3': 'SSL/TLS Fingerprints',
                                                'hassh': 'HASSH Fingerprints',
                                            }
                                            for rawdatafield in rawdatafields:
                                                if rawdatafield in json_response[field]:
                                                    rawdatavalue = ''
                                                    if rawdatafield == 'scan':
                                                        for scannedport in json_response[field][rawdatafield]:
                                                            port = scannedport['port']
                                                            proto = scannedport['protocol'].lower()
                                                            rawdatavalue += '`%s/%s`, ' % (port,proto)
                                                        rawdatavalue = rawdatavalue.strip(', ')
                                                    elif rawdatafield == 'web':
                                                        if 'useragents' in json_response[field][rawdatafield]:
                                                            rawdatavalue += '**User Agents**: `'+'`, `'.join([_ for _ in json_response[field][rawdatafield]['useragents'] if _])+'` '
                                                        if 'paths' in json_response[field][rawdatafield]:
                                                            rawdatavalue += '**Web Paths**: `'+'`, `'.join(json_response[field][rawdatafield]['paths'])+'` '
                                                    elif rawdatafield in ('ja3','hassh'):
                                                        fingerprints = {}
                                                        for entry in json_response[field][rawdatafield]:
                                                            fingerprint = entry['fingerprint'].lower()
                                                            port = str(entry['port'])
                                                            if fingerprint not in fingerprints:
                                                                fingerprints[fingerprint] = []
                                                            fingerprints[fingerprint].append(port)
                                                        for fingerprint in fingerprints:
                                                            rawdatavalue += '`%s` => `%s`: %s' % (rawdatafield, fingerprint, '`'+'`, `'.join(fingerprints[fingerprint])+'`')
                                                    else:
                                                        rawdatavalue = json_response[field][rawdatafield]
                                                    rawdatavalue = rawdatavalue.strip(' ')
                                                    if len(rawdatavalue):
                                                        message += '\n| **%s** | %s |' % (rawdatafields[rawdatafield],rawdatavalue)
                                        else:
                                            value = json_response[field]
                                            if value == True:
                                                value = 'Yes'
                                            if value == False:
                                                value = 'No'
                                            if len(value):
                                                message += '\n| **%s** | `%s` |' % (fields[field],value)
                                message += '\n\n'
                                messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching GreyNoise:\nError: `%s`' % (traceback.format_exc(),)})
    finally:
        return {'messages': messages}
