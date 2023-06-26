#!/usr/bin/env python3

import requests
from pathlib import Path
try:
    from commands.chatgpt import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/chatgpt/settings.py').is_file():
        try:
            from commands.chatgpt import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params):
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
