#!/usr/bin/env python3

import datetime
import math
import random
import re
import requests
import sys
import urllib
from pathlib import Path
try:
    from commands.tweetfeed import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/tweetfeed/settings.py').is_file():
        try:
            from commands.tweetfeed import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params):
    # Methods to query Tweetfeed info
    headers = {
        'Accept-Encoding': settings.CONTENTTYPE,
        'Content-Type': settings.CONTENTTYPE,
    }
    stripchars = '`\n\r\'\"\[\]'
    regex = re.compile('[%s]' % stripchars)
    params = regex.sub('',params[0]).replace('hxxp','http')
    messages = []
    try:
        if len(params)>3:
            APIENDPOINT = settings.APIURL['tweetfeed']['url']
            with requests.get(APIENDPOINT, headers=headers) as response:
                json_response = response.json()
                if len(json_response):
                    if len(json_response)<=settings.LIMIT:
                        for entry in json_response:
                            if params.lower() in entry['value'].lower() or params.lower() in ' '.join(entry['tags']):
                                if not len(messages):
                                    messages.append({'text': 'Tweetfeed search results for `%s`:' % (params,)})
                                    message = '\n'
                                    message += '\n| Date | User | Type | Value | Tags | URL |'
                                    message += '\n| :- | :- | :- | :- | :- | :- |'
                                    message += '\n'
                                for k in ('date', 'user', 'type', 'value', 'tags'):
                                    if k in entry:
                                        if isinstance(entry[k], list):
                                            v = '`, `'.join(entry[k])
                                        else:
                                            v = entry[k]
                                        message += '| `%s` ' % (v,)
                                    else:
                                        message += '| `N/A` '
                                if 'tweet' in entry:
                                    message += '| [Link](%s) ' % (entry['tweet'],)
                                else:
                                    message += '| `N/A` '
                                message += '|\n'
                        message += '\n\n'
                        messages.append({'text': message})
                    else:
                        messages.append({'text': 'Tweetfeed search exceeded limit of '+str(settings.LIMIT)+' results ('+str(len(response))+'). Raw JSON output:', 'uploads': [
                            {'filename': 'tweetfeed-'+params+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content}
                        ]})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching Tweetfeed:\nError:' + e})
    finally:
        return {'messages': messages}
