#!/usr/bin/env python3

import datetime
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
    params = ' '.join(params)
    headers = {
        'Accept-Encoding': settings.CONTENTTYPE,
        'Content-Type': settings.CONTENTTYPE,
    }
    messages = []
    try:
        if len(params)>3:
            stripchars = '`\n\r\'\"\\[\\]'
            regex = re.compile('[%s]' % stripchars)
            params = regex.sub('',params).replace('hxxp','http')
            APIENDPOINT = settings.APIURL['tweetfeed']['url']
            with requests.get(APIENDPOINT, headers=headers) as response:
                json_response = response.json()
                if len(json_response):
                    count = 0
                    for entry in json_response:
                        if params.lower() in entry['value'].lower() or params.lower() in ' '.join(entry['tags']).lower():
                            count += 1
                            if not len(messages):
                                messages.append({'text': 'Tweetfeed search results for `%s`:' % (params,)})
                                message = '\n'
                                message += '\n| Date | User | Type | Value | Tags | URL |'
                                message += '\n| :- | :- | :- | :- | :- | :- |'
                                message += '\n'
                            for k in ('date', 'user', 'type', 'value', 'tags'):
                                if k in entry:
                                    if isinstance(entry[k], list):
                                        if len(entry[k]):
                                            v = '`, `'.join(entry[k])
                                        else:
                                            v = 'N/A'
                                    else:
                                        v = entry[k]
                                    message += '| `%s` ' % (v,)
                                else:
                                    message += '| `N/A` '
                            if 'tweet' in entry:
                                message += '| [Link](%s) ' % (entry['tweet'],)
                            else:
                                message += '| `N/A` '
                            message += '|\n'
                    if count>0:
                        message += '\n\n'
                        messages.append({'text': message})
                if count>settings.LIMIT:
                    messages = [{'text': 'Tweetfeed search results exceeded the limit ('+str(count)+'/'+str(settings.LIMIT)+'). Raw JSON output:', 'uploads': [
                        {'filename': 'tweetfeed-'+params+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content}
                    ]}]
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching Tria.ge: %s\n%s' % (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
