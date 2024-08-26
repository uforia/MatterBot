#!/usr/bin/env python3

import collections
import datetime
import json
import pytz
import requests
import traceback
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
                "order": "Event.publish_timestamp desc",
            }
            data = {
                "returnformat": "json",
                "enforceWarninglist": "1",
                "searchAll": "1",
                "quickfilter": "1",
                "order": "Event.publish_timestamp desc",
                "value": params,
            }
            with requests.post(settings.APIENDPOINT, data=json.dumps(data), headers=headers) as response:
                answer = response.json()
                results = answer['response']
                message = ''
                if len(results)>0:
                    count = 0
                    fields = ('Date', 'Name', 'TTP(s)', 'IoC type', 'Comment', 'Event Tag(s)')
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
                        event = result['Event']
                        tags = set()
                        if count < settings.MAXHITS:
                            name = event['info'].replace('\n', ' ')
                            timestamp = datetime.datetime.fromtimestamp(int(event['timestamp']),pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                            ttps = set()
                            comments = set()
                            ioctypes = set()
                            tags = set()
                            attributes = []
                            if len(event['Attribute']):
                                attributes = event['Attribute']
                            elif len(event['Object']):
                                for mispobject in event['Object']:
                                    for attribute in mispobject['Attribute']:
                                        attributes.append(attribute)
                            for attribute in attributes:
                                if params in attribute['value']:
                                    comments.add(attribute['comment'])
                                    ttps.add(attribute['category'])
                                    ioctypes.add(attribute['type'].replace('|','` and `'))
                            if len(ttps):
                                ttps = '`'+'`, `'.join(ttps)+'`'
                            else:
                                ttps = '-'
                            if len(comments):
                                comments = '`'+'`, `'.join(comments).replace('\n', ', ').replace('http', 'hxxp')+'`'
                                if len(comments)<3:
                                    comments = '-'
                            else:
                                comments = '-'
                            if len(ioctypes):
                                ioctypes = '`'+'`, `'.join(ioctypes)+'`'
                            else:
                                ioctypes = '-'
                            if 'Tag' in event:
                                for tag in event['Tag']:
                                    tags.add(tag['name'])
                            if len(tags):
                                tags = '`'+'`, `'.join(tags)+'`'
                            else:
                                tags = '-'
                            url = settings.APIURL + '/events/view/' + event['id']
                            message += '| %s | [%s](%s) | %s | %s | %s | %s |\n' % (timestamp, name, url, ttps, ioctypes, comments, tags)
                            count += 1
                    message += '\n\n'
                    if count >= settings.MAXHITS:
                        message += '*Newest `%d` results displayed out of `%d` total, refer to your MISP instance for more comprehensive results. Empty TTP, IoC and Comments fields may indicate an inherited/related IoC.*' % (settings.MAXHITS, len(results))
                if len(message):
                    messages.append({'text': message})
        else:
            messages.append({'text': 'At least ask me something, %s!' % (username,)})
    except Exception as e:
        messages.append({'text': 'An error occurred searching MISP\nError: `%s`' % (traceback.format_exc(),)})
    finally:
        return {'messages': messages}
