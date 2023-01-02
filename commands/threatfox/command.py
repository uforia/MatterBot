#!/usr/bin/env python3

import httpx
import json
import re
from pathlib import Path
try:
    from commands.threatfox import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/threatfox/settings.py').is_file():
        try:
            from commands.threatfox import settings
        except ModuleNotFoundError: # local test run
            import settings

async def process(connection, channel, username, params):
    if len(params)>0:
        params = params[0]
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        message = "ThreatFox search for `%s`:\n" % params
        try:
            data = None
            hash_algo = None
            if re.search(r"^[A-Za-z0-9]{32}$", params):
                hash_algo = 'md5_hash'
            elif re.search(r"^[A-Za-z0-9]{40}$", params):
                hash_algo = 'sha1_hash'
            elif re.search(r"^[A-Za-z0-9]{64}$", params):
                hash_algo = 'sha256_hash'
            elif re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", params):
                data = {
                    'query': 'search_ioc',
                    'search_term': params.split(':')[0],
                }
            if hash_algo:
                data = {
                    'query': 'search_hash',
                    'hash': params,
                }
            if data:
                async with httpx.AsyncClient() as session:
                    response = await session.post(settings.APIURL['threatfox']['url'], json=data)
                    json_response = response.json()
                    if json_response['query_status'] == 'ok':
                        if 'data' in json_response:
                            data = json_response['data']
                            for sample in data:
                                id = sample['id']
                                ioc = sample['ioc']
                                threat = sample['threat_type_desc']
                                malware_printable = sample['malware_printable']
                                message += '- Threat: `%s`: `%s`' % (malware_printable, threat)
                                if 'tags' in sample:
                                    tags = sample['tags']
                                    message += ' | Tags: `' + '`, `'.join(tags) + '`'
                                threatfox_reference = 'https://threatfox.abuse.ch/ioc/%s' % id
                                message += ' | Reference: [ThreatFox ID %s](%s)' % (id, threatfox_reference)
                                message += '\n'
                            if len(data)>0:
                                return message.strip()
                    else:
                        return 'ThreatFox search for `%s` returned no results.' % params
        except Exception as e:
            return "An error occurred searching for `%s`:\nError: `%s`" % (params, e.message)
