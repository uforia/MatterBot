#!/usr/bin/env python3

import json
import re
import requests
import sys
import traceback
from pathlib import Path
try:
    from commands.unprotectit import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    from commands.loldrivers import defaults
    if Path('commands/loldrivers/settings.py').is_file():
        try:
            from commands.loldrivers import settings
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
                with requests.get(settings.APIURL['loldrivers']['url'], headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        with open(settings.CACHE, mode='w') as f:
                            cache = json.dumps(json_response)
                            f.write(cache)
                            message = "LOLDrivers cache rebuilt."
                            messages.append({'text': message})
            if Path(settings.CACHE).is_file():
                with open(settings.CACHE,'r') as f:
                    loldrivers = json.load(f)
                if re.search(r"^[A-Fa-f0-9]{32}$", query):
                    type = 'MD5'
                elif re.search(r"^[A-Fa-f0-9]{40}$", query):
                    type = 'SHA1'
                elif re.search(r"^[A-Fa-f0-9]{64}$", query):
                    type = 'SHA256'
                else:
                    type = 'File'
                for loldriver in loldrivers:
                    found = False
                    if type in ('MD5','SHA1','SHA256'):
                        if 'KnownVulnerableSamples' in loldriver:
                            for KnownVulnerableSample in loldriver['KnownVulnerableSamples']:
                                if type in KnownVulnerableSample:
                                    if query.lower() == KnownVulnerableSample[type]:
                                        found = True
                                if 'Authentihash' in KnownVulnerableSample:
                                    if type in KnownVulnerableSample['Authentihash']:
                                        if query.lower() == KnownVulnerableSample['Authentihash'][type]:
                                            found = True
                                if 'RichPEHeaderHash' in KnownVulnerableSample:
                                    if type in KnownVulnerableSample['RichPEHeaderHash']:
                                        if query.lower() == KnownVulnerableSample['RichPEHeaderHash'][type].lower():
                                            found = True
                    if type in ('File',):
                        filename = query.lower()
                        if filename == loldriver['Tags']:
                            found = True
                        elif 'KnownVulnerableSamples' in loldriver:
                            for KnownVulnerableSample in loldriver['KnownVulnerableSamples']:
                                if filename == KnownVulnerableSample['Filename'] or \
                                   filename == KnownVulnerableSample['InternalName'] or \
                                   filename == KnownVulnerableSample['OriginalFilename']:
                                    found = True
                    if found:
                        fields = [
                            'Category',
                            'Commands',
                            'KnownVulnerableSamples',
                            'MitreID',
                            'Detection',
                            'Resources',
                        ]
                        kvsfields = [
                            'Filename',
                            'OriginalFilename',
                            'InternalName',
                            'MD5',
                            'SHA1',
                            'SHA256',
                            'Authentihash',
                            'RichPEHeaderHash',
                            'Imports',
                            'ImportedFunctions',
                        ]
                        if 'Verified' in loldriver:
                            if loldriver['Verified'].lower() == 'true':
                                verified = ':white_check_mark:'
                            else:
                                verified = ':x:'
                        message =  '\n| LOLDrivers | **%s**: `%s` %s |' % (type,query,verified)
                        message += '\n| :- | :- |'
                        hitcount = 0
                        uploads = []
                        for field in fields:
                            if field == 'Commands':
                                value = loldriver[field]['Command']
                                value += ' (%s)' % loldriver[field]['Usecase']
                                message += '\n| **%s** | `%s` |' % (field,value)
                            elif field == 'Resources':
                                urls = []
                                for resource in loldriver[field]:
                                    urls.append('[%s](%s)' % (resource,resource))
                                    value = ', '.join(urls)
                                message += '\n| **%s** | %s |' % (field,value)
                            elif field == 'KnownVulnerableSamples':
                                for KnownVulnerableSample in loldriver[field]:
                                    hitcount += 1
                                    for kvsfield in kvsfields:
                                        if kvsfield in KnownVulnerableSample:
                                            value = KnownVulnerableSample[kvsfield]
                                            if kvsfield in ('Authentihash','RichPEHeaderHash'):
                                                hashes = []
                                                for hash in KnownVulnerableSample[kvsfield]:
                                                    hashes.append('**%s**: `%s`' % (hash,KnownVulnerableSample[kvsfield][hash]))
                                                    value = ', '.join(hashes)
                                                if len(value):
                                                    message += '\n| **%s** #%d | %s |' % (kvsfield,hitcount,value)
                                            if kvsfield in ('Imports','ImportedFunctions'):
                                                value = '`, `'.join(KnownVulnerableSample[kvsfield])
                                                if len(value):
                                                    message += '\n| **%s** #%d | `%s` |' % (kvsfield,hitcount,value)
                            elif field == 'Detection':
                                if len(loldriver[field]):
                                    filenames = []
                                    uploads = []
                                    for Detection in loldriver[field]:
                                        type = Detection['type'].replace('_',' ').title()
                                        url = Detection['value']
                                        try:
                                            with requests.get(url) as response:
                                                uploads.append({'filename': Path(url).name, 'bytes': response.content})
                                                filenames.append(Path(url).name)
                                        except:
                                            pass
                                    if len(uploads):
                                        value = '`, `'.join(filenames)
                                        message += '\n| **%s** | `%s`' % (field,value)
                            else:
                                value = loldriver[field]
                                if len(value):
                                    message += '\n| **%s** | `%s` |' % (field,value)
                        message += '\n\n'
                        if len(uploads):
                            messages.append({'text': message, 'uploads': uploads})
                        else:
                            messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'An error occurred in LOLDrivers:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
