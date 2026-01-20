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
                                    if query.lower() == KnownVulnerableSample[type].lower():
                                        found = True
                                if 'Authentihash' in KnownVulnerableSample:
                                    if type in KnownVulnerableSample['Authentihash']:
                                        if query.lower() == KnownVulnerableSample['Authentihash'][type].lower():
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
                        uploads = []
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
                        uploads = []
                        importFiles = set()
                        importFunctions = set()
                        authentihashes = set()
                        richpeheaderhashes = set()
                        for field in fields:
                            if field == 'Commands':
                                value = loldriver[field]['Command'] if len(loldriver[field]['Command']) else 'N/A'
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
                                    for kvsfield in kvsfields:
                                        if kvsfield in KnownVulnerableSample:
                                            value = KnownVulnerableSample[kvsfield]
                                            if kvsfield == 'Authentihash':
                                                for authentihash in KnownVulnerableSample[kvsfield]:
                                                    authentihashes.add(KnownVulnerableSample[kvsfield][authentihash])
                                            if kvsfield == 'RichPEHeaderHash':
                                                for richpeheaderhash in KnownVulnerableSample[kvsfield]:
                                                    richpeheaderhashes.add(KnownVulnerableSample[kvsfield][richpeheaderhash])
                                            if kvsfield == 'Imports':
                                                for importFile in KnownVulnerableSample[kvsfield]:
                                                    importFiles.add(importFile)
                                            if kvsfield == 'ImportedFunctions':
                                                for importFunction in KnownVulnerableSample[kvsfield]:
                                                    importFunctions.add(importFunction)
                            elif field == 'Detection':
                                if len(loldriver[field]):
                                    filenames = []
                                    for Detection in loldriver[field]:
                                        type = Detection['type'].replace('_',' ').title()
                                        url = Detection['value']
                                        try:
                                            with requests.get(url) as response:
                                                uploads.append({'filename': Path(url).name, 'bytes': b'xxxx'})
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
                        if len(authentihash):
                            message += '\n| **Authentihash** | `%s` |' % ('`, `'.join(authentihashes))
                        if len(richpeheaderhashes):
                            message += '\n| **RichPEHeaderHash** | `%s` |' % ('`, `'.join(richpeheaderhashes))
                        if len(importFiles):
                            message += '\n| **Imports** | `%s` |' % ('`, `'.join(importFiles))
                        if len(importFunctions):
                            message += '\n| **Imported Functions** | `%s` |' % ('`, `'.join(importFunctions))
                        message += '\n\n'
                        if len(uploads):
                            messages.append({'text': message, 'uploads': uploads})
                        else:
                            messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'An error occurred in LOLDrivers:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
