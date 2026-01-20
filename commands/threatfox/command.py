#!/usr/bin/env python3

import re
import requests
import traceback

### Dynamic configuration loader (do not change/edit)
import importlib
from pathlib import Path
_pkg_name = Path(__file__).parent.name
try:
    defaults_mod = importlib.import_module(f'commands.{_pkg_name}.defaults')
except ModuleNotFoundError:
    try:
        defaults_mod = importlib.import_module('defaults')
    except ModuleNotFoundError:
        print(f"Module {_pkg_name} could not be loaded due to a missing default configuration.")
try:
    settings_mod = importlib.import_module(f'commands.{_pkg_name}.settings')
except ModuleNotFoundError:
    try:
        settings_mod = importlib.import_module('settings')
    except ModuleNotFoundError:
        settings_mod = None
settings = {k: v for k, v in vars(defaults_mod).items() if not k.startswith('__')}
if settings_mod:
    settings.update({k: v for k, v in vars(settings_mod).items() if not k.startswith('__')})
from types import SimpleNamespace
settings = SimpleNamespace(**settings)
### Loader end, actual module functionality starts here

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        messages = []
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http')
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'Auth-Key': settings.APIURL['threatfox']['key'],
        }
        message = 'ThreatFox search for `%s`:\n' % (params,)
        try:
            data = None
            hash_algo = None
            if re.search(r"^[A-Fa-f0-9]{32}$", params):
                hash_algo = 'md5_hash'
            elif re.search(r"^[A-Fa-f0-9]{40}$", params):
                hash_algo = 'sha1_hash'
            elif re.search(r"^[A-Fa-f0-9]{64}$", params):
                hash_algo = 'sha256_hash'
            elif re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", params):
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
                with requests.post(settings.APIURL['threatfox']['url'], json=data, headers=headers) as response:
                    if response.status_code in (401,):
                        message = "Incorrect ThreatFox API key or not configured!"
                    else:
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
                                        if sample['tags']:
                                            tags = sample['tags']
                                            tags = '`, `'.join(tags) if isinstance(tags,list) else '`' + tags + '`'
                                            message += ' | Tags: `' + tags + '`'
                                    threatfox_reference = 'https://threatfox.abuse.ch/ioc/%s' % (id,)
                                    message += ' | Reference: [ThreatFox ID %s](%s)' % (id, threatfox_reference)
                                    message += '\n'
                                if len(data)>0:
                                    messages.append({'text': message.strip()})
        except Exception as e:
            messages.append({'text': 'A Python error occurred searching ThreatFox: %s\n%s' % (str(e),traceback.format_exc())})
        finally:
            return {'messages': messages}
