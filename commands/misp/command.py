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
    try:
        messages = []
        if len(params)>0:
            params = ' '.join(params).replace('[', '').replace(']', '').replace('hxxp','http')
            headers = {
                "Accept": settings.CONTENTTYPE,
                "Content-Type": settings.CONTENTTYPE,
                "Authorization": "%s" % (settings.APIKEY,),
                "enforceWarninglist": "1",
                "order": "Event.date desc"
            }
            data = '{"returnformat":"json", "value":"%s"}' % (params,)
            with requests.post(settings.APIENDPOINT, data=data, headers=headers) as response:
                answer = response.json()
                results = answer['response']['Attribute']
                resultset = set()
                if len(results)>0:
                    messages.append({'text': 'MISP search for `%s`:' % (params,)})
                    for result in results:
                        name = result['Event']['info'].replace('\n', ' ')
                        comment = result['Event']['comment'].replace('\n', ' ') if 'comment' in Event else None
                        timestamp = datetime.datetime.utcfromtimestamp(int(result['timestamp'])).strftime('%Y-%m-%dT%H:%M:%SZ')
                        category = result['category']
                        type = result['type'].replace('|','` and `')
                        to_ids = result['to_ids']
                        to_ids = "Yes" if to_ids else "No"
                        tags = [_['name'].split(':',1) for _ in result['Tag']] if 'Tag' in result else None
                        url = settings.APIURL + '/events/view/' + result['event_id']
                        message = "\n\n"
                        message += "| Event: [%s](%s) | Date/Time: `%s` |\n" % (name, url, timestamp)
                        message += "| :--- | -: |\n"
                        message += "| TTP Type / Kill-chain Phase | `%s` |\n" % (category,)
                        message += "| Indicator of Compromise type(s) | `%s` |\n" % (type,)
                        message += "| Suitable for IDS | `%s` |\n" % (to_ids,)
                        if comment:
                            message += "| Comment | `%s` |\n" % (comment,)
                        if tags:
                            for tag in tags:
                                if len(tag)>1:
                                    value = tag[1:].join(':').capitalize() if len(tag)>2 else tag[1]
                                else:
                                    value = "N/A"
                                message += "| *Extra Tag*: `%s` | `%s` |\n" % (tag[0].capitalize(), value)
                        message += "\n\n"
                        messages.append({'text': message})
                else:
                    messages.append({'text': 'MISP search for `%s` returned no results.' % (params,)})
        else:
            messages.append({'text': 'At least ask me something, %s!' % (username,)})
    except Exception as e:
        messages.append({'text': 'An error occurred querying MISP: `%s`' % (str(e),)})
    finally:
        return {'messages': messages}
