#!/usr/bin/env python3

import json
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
                with requests.get(settings.APIURL['bootloaders']['url'], headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        with open(settings.CACHE, mode='w') as f:
                            cache = json.dumps(json_response)
                            f.write(cache)
                            message = "Bootloaders cache rebuilt."
                            messages.append({'text': message})
            if Path(settings.CACHE).is_file():
                with open(settings.CACHE,'r') as f:
                    bootloaders = json.load(f)
                if re.search(r"^[A-Fa-f0-9]{32}$", query):
                    type = 'MD5'
                elif re.search(r"^[A-Fa-f0-9]{40}$", query):
                    type = 'SHA1'
                elif re.search(r"^[A-Fa-f0-9]{64}$", query):
                    type = 'SHA256'
                else:
                    type = 'File'
                for loldriver in bootloaders:
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
                        message =  '\n| Bootloaders | **%s**: `%s` %s |' % (type,query,verified)
                        message += '\n| :- | :- |'
                        uploads = []
                        importFiles = set()
                        importFunctions = set()
                        authentihashes = set()
                        richpeheaderhashes = set()
                        for field in fields:
                            if field == 'Commands':
                                value = loldriver[field]['Command'].replace('|','¦').replace('\n','; ').strip('; ') if len(loldriver[field]['Command']) else 'N/A'
                                value += ' (%s)' % loldriver[field]['Usecase'].replace('|','¦').replace('\n','; ').strip('; ')
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
                                                    if len(KnownVulnerableSample[kvsfield][authentihash]):
                                                        authentihashes.add(KnownVulnerableSample[kvsfield][authentihash])
                                            if kvsfield == 'RichPEHeaderHash':
                                                for richpeheaderhash in KnownVulnerableSample[kvsfield]:
                                                    if len(KnownVulnerableSample[kvsfield][richpeheaderhash]):
                                                        richpeheaderhashes.add(KnownVulnerableSample[kvsfield][richpeheaderhash])
                                            if kvsfield == 'Imports':
                                                for importFile in KnownVulnerableSample[kvsfield]:
                                                    if len(importFile):
                                                        importFiles.add(importFile)
                                            if kvsfield == 'ImportedFunctions':
                                                for importFunction in KnownVulnerableSample[kvsfield]:
                                                    if len(importFunction):
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
        messages.append({'text': 'An error occurred in Bootloaders:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
