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
                with requests.get(settings.APIURL['loobins']['url'], headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        with open(settings.CACHE, mode='w') as f:
                            cache = json.dumps(json_response)
                            f.write(cache)
                            message = "LOOBINS cache rebuilt."
                            messages.append({'text': message})
            if Path(settings.CACHE).is_file() and len(query)>=4:
                with open(settings.CACHE,'r') as f:
                    loobins = json.load(f)
                results = []
                query = query.lower()
                for loobin in loobins:
                    found = False
                    if query in loobin['name'].lower() or \
                        query in loobin['full_description'].lower() or \
                        query in ' '.join(loobin['paths']):
                        found = True
                    if found:
                        name = loobin['name'].replace('\n','. ').replace('|','-').replace('\\','')
                        description = loobin['short_description'].replace('\n','. ').replace('|','-').replace('\\','')
                        timestamp = loobin['created']
                        url = "https://loobins.io/binaries/%s" % (name.lower().replace(' ','_').replace('(','_').replace(')','_'),)
                        results.append(collections.OrderedDict({
                            'Name': name,
                            'Description': description,
                            'Updated': timestamp,
                            'Details': url,
                        }))
                if len(results):
                    message =  '**LOOBINS** search results for: `%s`\n' % (query,)
                    message += '\n| **Name** | **Description** | **Updated** | **Details** |'
                    message += '\n| :- | :- | -: | :- |'
                    for result in results:
                        message += f"\n| {result['Name']} | {result['Description']} | {result['Updated']} | [Link]({result['Details']}) |"
                    message += '\n\n'
                    messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'An error occurred in LOOBINS:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
