#!/usr/bin/env python3

import datetime
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
                message = 'MISP search for `%s`:' % (params,)
                for result in results:
                    name = result['Event']['info'].replace('\n', ' ')
                    timestamp = datetime.datetime.utcfromtimestamp(int(result['timestamp'])).strftime('%Y-%m-%dT%H:%M:%SZ')
                    category = result['category']
                    type = result['type']
                    to_ids = result['to_ids']
                    to_ids = "Yes" if to_ids else "No"
                    if 'Tag' in result:
                        tags = [_['name'].split(':') for _ in result['Tag']]
                    url = settings.APIURL + '/events/view/' + result['event_id']
                    message += "\n\n"
                    message += "| Event: [%s](%s) | Date/Time: `%s` |\n" % (name, url, timestamp)
                    message += "| :--- | -: |\n"
                    message += "| TTP type / Kill-chain phase | %s |\n" % (category,)
                    message += "| Indicator of Compromise type | %s |\n" % (type,)
                    message += "| Suitable for IDS | %s |\n" % (to_ids,)
                    if tags:
                        for tag in tags:
                            message += "| *Extra tag*: %s | %s |\n" % (tag[0].capitalize(), tag[1].capitalize())
                message += "\n\n"
            else:
                message = 'MISP search for `%s` returned no results.' % (params,)
            return {'messages': [
                {'text': message.strip()}
            ]}
    else:
        return {'messages': [
            {'text': 'At least ask me something, %s!' % (username,)}
        ]}
