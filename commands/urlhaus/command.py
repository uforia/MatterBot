#!/usr/bin/env python3

import re
import requests
import traceback

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http')
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'Auth-Key': settings.APIURL['urlhaus']['key'],
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
                        message = "Incorrect URLhaus API key or not configured!"
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
                        message = "Incorrect URLhaus API key or not configured!"
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
            messages.append({'text': 'A Python error occurred searching URLhaus: %s\n%s' % (str(e),traceback.format_exc())})
        finally:
            return {'messages': messages}