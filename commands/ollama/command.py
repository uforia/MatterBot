#!/usr/bin/env python3

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
        stripchars = r'`\n\r\'\"'
        regex = re.compile(stripchars)
        if len(params)>0:
            params = regex.sub('. ', ' '.join(params), re.IGNORECASE)
            headers = {
                "Content-Type": settings.CONTENTTYPE,
            }
            data = {
                "model": settings.MODEL,
                "stream": False,
                "prompt": params,
                "keep_alive": -1,
                "options": {
                    "temperature": settings.TEMPERATURE,
                }
            }
            messages = []
            with requests.post(settings.APIENDPOINT, json=data, headers=headers) as response:
                answer = response.json()
                reply = None
                if 'response' in answer:
                    message = f'**AI LLM** Prompt: `{params}` - Answer:\n'
                    message += ">"+answer['response']
                    message += '\n'
                    messages.append({'text': message})
                else:
                    messages.append({'text': 'No answer was given by the AI LLM.'})
        else:
            messages.append({'text': f"At least ask me something, {username}!"})
    except Exception as e:
        messages.append({'text': 'An error occurred querying the AI LLM: `%s`:\n%s' % (params, traceback.format_exc())},)
    finally:
        return {'messages': messages}
