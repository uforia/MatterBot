#!/usr/bin/env python3

import collections
import json
import re
import requests
import sys
import traceback
from pathlib import Path
try:
    from commands.loobins import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    from commands.loobins import defaults
    if Path('commands/loobins/settings.py').is_file():
        try:
            from commands.loobins import settings
        except ModuleNotFoundError: # local test run
            import defaults
            import settings

def process(command, channel, username, params, files, conn):
    messages = []
    try:
        if len(params):
            stripchars = ' `\n\r\'\"'
            regex = re.compile('[%s]' % stripchars)
            headers = {
                'Content-Type': settings.CONTENTTYPE,
            }
            query = params[0]
            if query == 'rebuildcache' or not Path(settings.CACHE).is_file():
                with requests.get(settings.APIURL['loobins']['url'], headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        with open(settings.CACHE, mode='w') as f:
                            cache = json.dumps(json_response)
                            f.write(cache)
                            message = "LOOBINS cache rebuilt."
                            messages.append({'text': message})
            if Path(settings.CACHE).is_file() and len(query)>=4:
                with open(settings.CACHE,'r') as f:
                    loobins = json.load(f)
                results = []
                query = query.lower()
                for loobin in loobins:
                    found = False
                    if query in loobin['name'].lower() or \
                        query in loobin['full_description'].lower() or \
                        query in ' '.join(loobin['paths']):
                        found = True
                    if found:
                        name = loobin['name'].replace('\n','. ').replace('|','-').replace('\\','')
                        description = loobin['short_description'].replace('\n','. ').replace('|','-').replace('\\','')
                        timestamp = loobin['created']
                        url = "https://loobins.io/binaries/%s" % (name.lower().replace(' ','_').replace('(','_').replace(')','_'),)
                        results.append(collections.OrderedDict({
                            'Name': name,
                            'Description': description,
                            'Updated': timestamp,
                            'Details': url,
                        }))
                if len(results):
                    message =  '**LOOBINS** search results for: `%s`\n' % (query,)
                    message += '\n| **Name** | **Description** | **Updated** | **Details** |'
                    message += '\n| :- | :- | -: | :- |'
                    for result in results:
                        message += f"\n| {result['Name']} | {result['Description']} | {result['Updated']} | [Link]({result['Details']}) |"
                    message += '\n\n'
                    messages.append({'text': message})
    except Exception as e:
        messages.append({'text': 'An error occurred in LOOBINS:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
