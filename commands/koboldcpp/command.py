#!/usr/bin/env python3

import json
import random
import re
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
        stripchars = r'`\n\r\'\"'
        regex = re.compile(stripchars)
        params = json.dumps(regex.sub(' ', params, re.IGNORECASE))
        headers = {
            "Content-Type": settings.CONTENTTYPE,
            "Authorization": "Bearer %s" % settings.APIURL['koboldcpp']['key'],
        }
        randkey = random.randint(0,9999)
        data = {
            "n": 1,
            "prompt": f"\n### Instruction:\n{params}\n### Response:\n",
            "stop_sequence": ["### Instruction:", "### Response:"],
            "temperature": settings.TEMP,
            "max_context_length": settings.CL,
            "max_length": settings.L,
            "rep_pen": 1.07,
            "rep_pen_range": 360,
            "rep_pen_slope": 0.7,
            "tfs": 1,
            "top_a": 0,
            "top_k": 100,
            "top_p": 0.92,
            "typical": 1,
            "sampler_order": [6, 0, 1, 3, 4, 2, 5],
            "memory": "",
            "trim_stop": True,
            "min_p": 0,
            "dynatemp_range": 0,
            "dynatemp_exponent": 1,
            "smoothing_factor": 0,
            "banned_tokens": [],
            "render_special": False,
            "logprobs": False,
            "presence_penalty": 0,
            "logit_bias": {},
            "use_default_badwordsids": False,
            "bypass_eos": False,
            "quiet": True,
            "genkey": "KCPP{:03d}".format(randkey)
        }
        with requests.post(settings.APIURL['koboldcpp']['url'], json=json.dumps(data), headers=headers) as response:
            answers = response.json()
            if 'results' in answers:
                num = 1
                messages = []
                for answer in answers['results']:
                    message = f'**KoboldCPP LLM** Prompt: `{params}` - Answer {num}:\n'
                    message += ">"+answer['text']
                    message += '\n'
                    messages.append({'text': message})
            if len(messages):
                return {'messages': messages}
    else:
        return {'messages': [
            {'text': 'At least ask me something, %s!' % (username,)},
        ]}
