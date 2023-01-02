#!/usr/bin/env python3

import aiohttp
import json
import pymisp
from pathlib import Path
try:
    from commands.misp import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/misp/settings.py').is_file():
        try:
            from commands.misp import settings
        except ModuleNotFoundError: # local test run
            import settings

async def process(connection, channel, username, params):
    if len(params)>0:
        params = ' '.join(params)
        headers = {
            "Content-Type": settings.CONTENTTYPE,
            "Authorization": "%s" % settings.APIKEY,
            "Accept": settings.CONTENTTYPE,
            "enforceWarninglist": "1",
        }
        data = '{"returnformat":"json", "value":"%s"}' % params
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(settings.APIENDPOINT, data=data) as response:
                answer = await response.json()
                results = answer['response']['Attribute']
                resultset = set()
                if len(results)>0:
                    message = 'MISP search for `%s`:\n' % params
                    for result in results:
                        line = '- `' + result['Event']['info'].replace('\n', ' ') + '`: ' + settings.APIURL + '/events/view/' + result['event_id'] + '\n'
                        if line not in resultset:
                            resultset.add(line)
                            message += line
                else:
                    message = 'MISP search for `%s` returned no results.' % params
                return message.strip()
    else:
        return "At least ask me something, %s!" % username
