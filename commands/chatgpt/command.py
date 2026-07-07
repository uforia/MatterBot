#!/usr/bin/env python3

import requests

from matterbot_formatting import sanitize_block, sanitize_inline

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

def _format_answer(content):
    """Render a model answer inside a fenced code block, neutralizing any
    ``` in the (untrusted) model output so it cannot break out of the fence."""
    return '\n```%s\n```' % (sanitize_block(content),)


def _format_error(message):
    """Render an API error message inside inline code, stripping backticks so
    the (upstream) message cannot break out of the inline-code wrapper."""
    return 'An error occurred querying OpenAI: `%s`' % (sanitize_inline(message),)


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
        with requests.post(settings.APIENDPOINT, json=data, headers=headers, timeout=(10, 30)) as response:
            answer = response.json()
            reply = None
            if 'error' in answer:
                reply = _format_error(answer['error']['message'])
            if 'choices' in answer:
                reply = _format_answer(answer['choices'][0]['message']['content'][1:])
            if reply:
                return {'messages': [
                    {'text': reply},
                ]}
    else:
        return {'messages': [
            {'text': 'At least ask me something, %s!' % (username,)},
        ]}
