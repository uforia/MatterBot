#!/usr/bin/env python3

import re
import requests
import sys
import traceback
from pathlib import Path
try:
    from commands.botscout import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/botscout/settings.py').is_file():
        try:
            from commands.botscout import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    headers = {
        'User-Agent': 'MatterBot integration for BotScout v1.0',
    }
    if len(params):
        query = regex.sub('',params[0])
        try:
            url = settings.APIURL['botscout']['url']+f"{query}"
            if settings.APIURL['botscout']['key']:
                url += f"&key={settings.APIURL['botscout']['key']}"
            with requests.get(url, headers=headers) as response:
                if response.status_code in (200,):
                    message = f"| BotScout results | `{query}` |\n"
                    message += "| :- | -: |\n"
                    responsefields = response.content.split(b'|')
                    verdict = responsefields[0].decode('utf-8').lower()
                    message += "| **Verdict** "
                    message += "| `Bot / Malicious` :red_circle: |\n" if verdict == 'y' else "| `Safe / Unknown` :large_green_circle: |\n"
                    results = responsefields[2:]
                    count = 0
                    fieldmap = {
                        'ip': 'IP Address',
                        'mail': 'E-mail Address',
                        'name': 'Name / Text',
                    }
                    while count<len(results):
                        type = results[count+1].decode('utf-8').lower()
                        if type in fieldmap:
                            type = fieldmap[type]
                        hits = results[count].decode('utf-8')
                        message += f"| **Seen As** | `{type}` |\n"
                        message += f"| **Detected** | `{hits}` times |\n"
                        count += 2
                    message += "\n\n"
                    messages.append({'text': message})
                else:
                    messages.append({'text': 'An error occurred querying the BotScout API:\nError: `%s`' % (response.content,)})
        except:
            messages.append({'text': 'An error occurred in the BotScout module:\nError: `%s`' % (traceback.format_exc(),)})
        finally:
            return {'messages': messages}
