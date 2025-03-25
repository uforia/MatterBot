#!/usr/bin/env python3

import json
import re
import requests
import sys
import traceback
from pathlib import Path
try:
    from commands.lolbas import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    from commands.lolbas import defaults
    if Path('commands/lolbas/settings.py').is_file():
        try:
            from commands.lolbas import settings
        except ModuleNotFoundError: # local test run
            import defaults
            import settings

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
                            print(lolbas['Detection'])
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
