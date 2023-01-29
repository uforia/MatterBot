#!/usr/bin/env python3

import json
import pymisp
import requests
from pathlib import Path
try:
    from commands.misp import defaults as settings
    if settings.HELP:
        HELP = settings.HELP
except ModuleNotFoundError: # local test run
    import defaults as settings
    if settings.HELP:
        HELP = settings.HELP
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/misp/settings.py').is_file():
        try:
            from commands.misp import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params):
    if len(params)>0:
        params = ' '.join(params).replace('[', '').replace(']', '').replace('hxxp','http')
        headers = {
            "Content-Type": settings.CONTENTTYPE,
            "Authorization": "%s" % (settings.APIKEY,),
            "Accept": settings.CONTENTTYPE,
            "enforceWarninglist": "1",
        }
        data = '{"returnformat":"json", "value":"%s"}' % (params,)
        with requests.post(settings.APIENDPOINT, data=data, headers=headers) as response:
            answer = response.json()
            results = answer['response']['Attribute']
            resultset = set()
            if len(results)>0:
                message = 'MISP search for `%s`:\n' % (params,)
                for result in results:
                    line = '- `' + result['Event']['info'].replace('\n', ' ') + '`: ' + settings.APIURL + '/events/view/' + result['event_id'] + '\n'
                    if line not in resultset:
                        resultset.add(line)
                        message += line
            else:
                message = 'MISP search for `%s` returned no results.' % (params,)
            return {'messages': [
                {'text': message.strip()},
            ]}
    else:
        return {'messages': [
            {'text': 'At least ask me something, %s!' % (username,)}
        ]}
