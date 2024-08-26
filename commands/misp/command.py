#!/usr/bin/env python3

import collections
import datetime
import json
import pytz
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

def process(command, channel, username, params, files, conn):
    try:
        messages = []
        if len(params)>0:
            params = ' '.join(params).replace('[', '').replace(']', '').replace('hxxp','http')
            headers = {
                "Accept": settings.CONTENTTYPE,
                "Content-Type": settings.CONTENTTYPE,
                "Authorization": "%s" % (settings.APIKEY,),
                "enforceWarninglist": "1",
                "searchAll": "1",
                "quickfilter": "1",
                "order": "Event.date desc",
            }
            data = {
                "returnformat": "json",
                "enforceWarninglist": "1",
                "searchAll": "1",
                "quickfilter": "1",
                "order": "Event.date desc",
                "value": params,
            }
            with requests.post(settings.APIENDPOINT, data=json.dumps(data), headers=headers) as response:
                answer = response.json()
                results = answer['response']['Attribute']
                if len(results)>0:
                    count = 0
                    fields = ('Date', 'Name', 'TTP(s)', 'IoC type', 'IDS', 'Comment', 'Tag(s)')
                    message = '**MISP search for `%s`: `%d` results**\n\n' % (params,len(results))
                    for field in fields:
                        message += '| **%s** ' % (field,)
                    message += '|\n'
                    for field in fields:
                        if field in ('Date', 'IDS'):
                            message += '| -: '
                        else:
                            message += '| :- '
                    message += '|\n'
                    for result in results:
                        tags = set()
                        if count < 11:
                            name = result['Event']['info'].replace('\n', ' ')
                            comment = result['Event']['comment'].replace('\n', ' ') if 'comment' in result['Event'] else '-'
                            timestamp = datetime.datetime.fromtimestamp(int(result['timestamp']),pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                            ttp = result['category']
                            ioctype = '`'+result['type'].replace('|','` and `')+'`'
                            ids = 'Yes' if result['to_ids'] else 'No'
                            rawtags = [_['name'].split(':',1) for _ in result['Tag']] if 'Tag' in result else None
                            if rawtags:
                                for rawtag in rawtags:
                                    for tag in rawtag:
                                        tags.add(tag)
                            if len(tags):
                                tags = '`'+'`, `'.join(tags)+'`'
                            else:
                                tags = '-'
                            url = settings.APIURL + '/events/view/' + result['event_id']
                            message += '| %s | [%s](%s) | %s | %s | %s | %s | %s |\n' % (timestamp, name, url, ttp, ioctype, ids, comment, tags)
                            count += 1
                    message += '\n\n'
                    if count >= 10:
                        message += '*More than 10 results (`%d`) found. Refer to your MISP instance for more comprehensive results.*' % (len(results),)
                    messages.append({'text': message})
        else:
            messages.append({'text': 'At least ask me something, %s!' % (username,)})
    except Exception as e:
        messages.append({'text': 'An error occurred querying MISP: `%s`' % (str(e),)})
    finally:
        return {'messages': messages}
