#!/usr/bin/env python3

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
