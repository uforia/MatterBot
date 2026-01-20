#!/usr/bin/env python3

import requests

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
    if len(params)>0:
        params = ' '.join(params)
        headers = {
            "Content-Type": settings.CONTENTTYPE,
            "Authorization": "Bearer %s" % (settings.APIKEY,),
        }
        data = {
            "model": settings.MODEL,
            "temperature": settings.TEMPERATURE,
            "max_tokens": settings.MAX_TOKENS,
            "prompt": params,
        }
        with requests.post(settings.APIENDPOINT, json=data, headers=headers) as response:
            answer = response.json()
            reply = None
            if 'error' in answer:
                reply = "An error occurred querying OpenAI: `"+answer['error']['message']+'`'
            if 'choices' in answer:
                reply = '\n```%s\n```' % (answer['choices'][0]['message']['content'][1:],)
            if reply:
                return {'messages': [
                    {'text': reply},
                ]}
    else:
        return {'messages': [
            {'text': 'At least ask me something, %s!' % (username,)},
        ]}
