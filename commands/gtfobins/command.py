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
                with requests.get(settings.APIURL['gtfobins']['url'], headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        with open(settings.CACHE, mode='w') as f:
                            cache = json.dumps(json_response)
                            f.write(cache)
                            message = "GTFOBins cache rebuilt."
                            messages.append({'text': message})
            if Path(settings.CACHE).is_file():
                with open(settings.CACHE,'r') as f:
                    gtfobins = json.load(f)
                fields = [
                    'Commands',
                    'Full_Path',
                    'Resources',
                ]
                filename = query.lower()
                if filename in gtfobins:
                    message =  "\n| **GTFOBins** | `%s` |" % (filename,)
                    message += "\n| :- | :- |"
                    description = gtfobins[filename]['description'] if gtfobins[filename]['description'] else 'N/A'
                    message += "\n| **Description** | %s |" % (description,)
                    functions = gtfobins[filename]['functions']
                    count = 0
                    for function in functions:
                        for example in functions[function]:
                            count += 1
                            description = example['description'].replace('/gtfobins/','https://gtfobins.github.io/gtfobins/') if 'description' in example else None
                            if description:
                                message += '\n| %d: **Description** | %s ' % (count,description)
                            code = example['code'].replace('|','¦').replace('\n','; ').strip('; ')
                            message += "\n| %d: **%s** | `%s` |" % (count,function,code)
                    message += "\n\n"
                    messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'An error occurred in GTFOBins:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
