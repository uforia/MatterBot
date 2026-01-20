#!/usr/bin/env python3

import collections
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
                with requests.get(settings.APIURL['lolrmm']['url'], headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        with open(settings.CACHE, mode='w') as f:
                            cache = json.dumps(json_response)
                            f.write(cache)
                            message = "LOLRMM cache rebuilt."
                            messages.append({'text': message})
            if Path(settings.CACHE).is_file() and len(query)>=4:
                with open(settings.CACHE,'r') as f:
                    lolrmms = json.load(f)
                results = []
                query = query.lower()
                for lolrmm in lolrmms:
                    found = False
                    if query in lolrmm['Name'].lower() or \
                        query in lolrmm['Description'].lower():
                        found = True
                    networkartifacts = set()
                    if 'Network' in lolrmm['Artifacts']:
                        if lolrmm['Artifacts']['Network']:
                            if len(lolrmm['Artifacts']['Network']):
                                for networkartifact in lolrmm['Artifacts']['Network']:
                                    if 'Domains' in networkartifact:
                                        if len(networkartifact['Domains']):
                                            for domain in networkartifact['Domains']:
                                                if query in domain.lower():
                                                    found = True
                    if 'Disk' in lolrmm['Artifacts']:
                        if lolrmm['Artifacts']['Disk']:
                            if len(lolrmm['Artifacts']['Disk']):
                                for diskartifact in lolrmm['Artifacts']['Disk']:
                                    if 'File' in diskartifact:
                                        if len(diskartifact['File']):
                                            for file in diskartifact['File']:
                                                if query in file.lower():
                                                    found = True
                    if 'Registry' in lolrmm['Artifacts']:
                        if lolrmm['Artifacts']['Registry']:
                            if len(lolrmm['Artifacts']['Registry']):
                                for registrypathlist in lolrmm['Artifacts']['Registry']:
                                    if query in registrypathlist['Path'].lower():
                                        found = True
                    if 'InstallationPaths' in lolrmm['Details']:
                        if lolrmm['Details']['InstallationPaths']:
                            if len(lolrmm['Details']['InstallationPaths']):
                                if query in " ".join(lolrmm['Details']['InstallationPaths']).lower().replace('*',''):
                                    found = True
                    if found:
                        name = lolrmm['Name'].replace('\n','. ').replace('|','-').replace('\\','')
                        description = lolrmm['Description'].replace('\n','. ').replace('|','-').replace('\\','')
                        timestamp = lolrmm['LastModified']
                        url = "https://lolrmm.io/tools/%s" % (name.lower().replace(' ','_').replace('(','_').replace(')','_'),)
                        results.append(collections.OrderedDict({
                            'Name': name,
                            'Description': description,
                            'Updated': timestamp,
                            'Details': url,
                        }))
                if len(results):
                    message =  '**LOLRMM** search results for: `%s`\n' % (query,)
                    message += '\n| **Name** | **Description** | **Updated** | **Details** |'
                    message += '\n| :- | :- | -: | :- |'
                    for result in results:
                        message += f"\n| {result['Name']} | {result['Description']} | {result['Updated']} | [Link]({result['Details']}) |"
                    message += '\n\n'
                    messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'An error occurred in LOLRMM:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
