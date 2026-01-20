#!/usr/bin/env python3

import json
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
    messages = []
    try:
        if len(params):
            stripchars = ' `\n\r\'\"'
            regex = re.compile('[%s]' % stripchars)
            headers = {
                'Content-Type': settings.CONTENTTYPE,
            }
            query = params[0]
            if query == 'rebuildcache' or not Path(settings.CACHE).is_file():
                with requests.get(settings.APIURL['lolbas']['url'], headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        with open(settings.CACHE, mode='w') as f:
                            cache = json.dumps(json_response)
                            f.write(cache)
                            message = "LOLBAS cache rebuilt."
                            messages.append({'text': message})
            if Path(settings.CACHE).is_file():
                with open(settings.CACHE,'r') as f:
                    lolbass = json.load(f)
                fields = [
                    'Commands',
                    'Full_Path',
                    'Resources',
                ]
                for lolbas in lolbass:
                    found = False
                    filename = query.lower()
                    if filename == lolbas['Name'].lower():
                        uploads = []
                        description = lolbas['Description']
                        message =  '\n| **LOLBAS** | `%s` |' % (filename,)
                        message += '\n| :- | :- |'
                        message += '\n| **Description** | `%s` |' % (description,)
                        for field in fields:
                            if field == 'Commands':
                                count = 0
                                for command in lolbas['Commands']:
                                    count += 1
                                    cmd = command['Command']
                                    usecase = command['Usecase']
                                    privs = command['Privileges']
                                    mitreid = command['MitreID']
                                    message += '\n| **Command** #%d | `%s`: %s |' % (count,cmd,usecase)
                                    message += '\n| **Context** #%d | MitreID: `%s` - Privileges: `%s` |' % (count,mitreid,privs)
                            if field == 'Full_Path':
                                count = 0
                                full_paths = set()
                                for full_path in lolbas['Full_Path']:
                                    count += 1
                                    full_paths.add(full_path['Path'])
                                message += '\n| **Full Paths** | %d: `%s` |' % (count,'`, `'.join(full_paths))
                            if field == 'Resources':
                                count = 0
                                urls = set()
                                for resource in lolbas['Resources']:
                                    count += 1
                                    url = resource['Link']
                                    urls.add('[%s](%s)' % (url,url))
                                message += '\n| **URLs** | %d: %s |' % (count,', '.join(urls))
                        if 'Detection' in lolbas:
                            urls = set()
                            detections = set()
                            iocs = set()
                            for detection in lolbas['Detection']:
                                for type in detection:
                                    detections.add(type)
                                    if 'http' in detection[type]:
                                        urls.add(detection[type])
                                    else:
                                        iocs.add(detection[type])
                            try:
                                for url in urls:
                                    with requests.get(url, headers=headers) as response:
                                        uploads.append({'filename': Path(url).name, 'bytes': response.content})
                            except:
                                pass
                        if len(detections):
                            message += '\n| **Detections** | `%s`, `%s` |' % ('`, `'.join(detections), '`, `'.join(iocs))
                        if len(uploads):
                            messages.append({'text': message, 'uploads': uploads})
                        else:
                            messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'An error occurred in LOLBAS:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
