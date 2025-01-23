#!/usr/bin/env python3

import random
import requests
from pathlib import Path
try:
    from commands.llm import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/llm/settings.py').is_file():
        try:
            from commands.llm import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        params = ' '.join(params)
        headers = {
            "Content-Type": settings.CONTENTTYPE,
            "Authorization": "Bearer %s" % settings.APIURL['llm']['key'],
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
        with requests.post(settings.APIURL['llm']['url'], json=data, headers=headers) as response:
            answers = response.json()
            if 'results' in answers:
                num = 1
                messages = []
                for answer in answers['results']:
                    message = f'**AI LLM** Prompt: `{params}` - Answer {num}:\n'
                    message += ">"+answer['text']
                    message += '\n'
                    messages.append({'text': message})
            if len(messages):
                return {'messages': messages}
    else:
        return {'messages': [
            {'text': 'At least ask me something, %s!' % (username,)},
        ]}
