#!/usr/bin/env python3

import json
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.urlhaus import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/urlhaus/settings.py').is_file():
        try:
            from commands.urlhaus import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http')
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'Auth-Key': settings.APIURL['threatfox']['key'],
        }
        try:
            type = None
            messages = []
            if re.search(r"^[A-Fa-f0-9]{32}$", params):
                hash_algo = 'md5_hash'
                data = { hash_algo: params }
                type = 'hash'
            elif re.search(r"^[A-Fa-f0-9]{40}$", params):
                hash_algo = 'sha1_hash'
                data = { hash_algo: params }
                type = 'hash'
            elif re.search(r"^[A-Fa-f0-9]{64}$", params):
                hash_algo = 'sha256_hash'
                data = { hash_algo: params }
                type = 'hash'
            elif re.search(r"^[hH][tT][tT][pP]([sS])?\:\/\/.+", params):
                data = { 'url': params }
                type = 'url'
            if type == 'url':
                with requests.post(settings.APIURL['urlhaus']['url'], data=data) as response:
                    if response.status_code in (401,):
                        message = "Incorrect ThreatFox API key or not configured!"
                    else:
                        json_response = response.json()
                        if json_response['query_status'] == 'ok':
                            message = 'URLhaus search for `%s`:\n' % (params,)
                            urlhaus_reference = json_response['urlhaus_reference']
                            id = json_response['id']
                            threat = json_response['threat']
                            url_status = json_response['url_status']
                            host = json_response['host']
                            payloads = json_response['payloads']
                            tags = json_response['tags']
                            message += '- Threat: `%s`' % (threat,)
                            if tags:
                                message += ' | Tags: `' + '`, `'.join(tags) + '`'
                            if payloads:
                                filenames = set()
                                message += ' | Payload(s): '
                                for payload in payloads:
                                    filename = payload['filename']
                                    if filename not in filenames:
                                        filenames.add(filename)
                                        message += '`%s` ' % (filename,)
                            message += ' | Status: `%s`' % (url_status,)
                            message += ' | Reference: [URLhaus ID %s](%s)' % (id, urlhaus_reference)
                            message += '\n'
                            messages.append({'text': message.strip()})
            if type == 'hash':
                with requests.post(settings.APIURL['urlhaus']['payload'], data=data) as response:
                    if response.status_code in (401,):
                        message = "Incorrect ThreatFox API key or not configured!"
                    else:
                        json_response = response.json()
                        if json_response['query_status'] == 'ok':
                            urls = json_response['urls']
                            file_type = json_response['file_type']
                            if urls:
                                message = 'URLhaus search for `%s`:\n' % (params,)
                                for url in urls:
                                    id = url['url_id']
                                    urlhaus_reference = url['urlhaus_reference']
                                    link = url['url']
                                    filename = url['filename']
                                    message += '- URL: `%s`' % (link,)
                                    message += ' | Payload: `%s` (%s)' % (filename, file_type)
                                    message += ' | Reference: [URLhaus ID %s](%s)' % (id, urlhaus_reference)
                            messages.append({'text': message.strip()})
        except Exception as e:
            messages.append({'text': 'A Python error occurred searching ThreatFox: %s\n%s' % (str(e),traceback.format_exc())})
        finally:
            return {'messages': messages}