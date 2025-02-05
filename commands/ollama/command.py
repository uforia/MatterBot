#!/usr/bin/env python3

import requests
import traceback
from pathlib import Path
try:
    from commands.ollama import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/ollama/settings.py').is_file():
        try:
            from commands.ollama import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    messages = []
    try:
        if len(params)>0:
            params = ' '.join(params)
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
