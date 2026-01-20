#!/usr/bin/env python3

import base64
import collections
import re
import requests
import traceback
import urllib.parse

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here

def process(command, channel, username, params, files, conn):
    stripchars = r'\|\`\r\n\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'MatterBot RansomLook.io API integration',
    }
    try:
        query = None
        querytype = None
        limit = None
        messages = []
        uploads = []
        if len(params)>0:
            querytypes = (
                'group',
                'groups',
                'market',
                'markets',
                'posts',
                'tgchannels',
                'tgmessages',
            )
            querytype = params[0].lower()
            if not querytype in querytypes:
                messages.append({'text': 'Please specify one of `%s`!' % '`, `'.join(querytypes)})
            if len(params)>1:
                query = params[1:]
                try:
                    if isinstance(int(query[-1]),int):
                        limit = int(query[-1])
                        query = query[:-1]
                except ValueError:
                    limit = int(settings.LIMIT)
                query = ' '.join(query)
            else:
                limit = int(settings.LIMIT)
        if querytype:
            if querytype == 'group':
                if query:
                    endpoint = settings.APIURL['ransomlook']['url']+'groups'
                    with requests.get(url=endpoint, headers=headers) as response:
                        json_response = response.json()
                        if len(json_response):
                            candidates = []
                            for group in json_response:
                                if query.lower() in group.lower():
                                    candidates.append(group)
                        if len(candidates)>1:
                            message = 'Please be more specific, as multiple groups match your query: `%s`' % '`, `'.join(candidates)
                            messages.append({'text': message})
                        else:
                            endpoint = settings.APIURL['ransomlook']['url']+f"group/{candidates[0]}"
                            with requests.get(url=endpoint, headers=headers) as response:
                                groupinfo = response.json()[0]
                                if len(response.json())>1:
                                    posts = response.json()[1]
                                if len(groupinfo):
                                    message = f"**Ransomlook Group Information for `{query}`**\n"
                                    message += '\n\n'
                                    meta = groupinfo['meta'] if groupinfo['meta'] else 'N/A'
                                    message += f"**Description:** `{meta}`\n\n"
                                    if 'locations' in groupinfo:
                                        locations = groupinfo['locations']
                                        fields = collections.OrderedDict({
                                            'fqdn': 'FQDN',
                                            'title': 'Title',
                                            'available': 'Active',
                                            'updated': 'Last Update',
                                        })
                                        for field in fields:
                                            message += f"| {fields[field]} "
                                        message += '|\n'
                                        for field in fields:
                                            if field in ('fqdn', 'title'):
                                                message += f"| :- "
                                            else:
                                                message += f"| -: "
                                        message += '|\n'
                                        for location in locations:
                                            for field in fields:
                                                if field in location:
                                                    if field in ('available',):
                                                        value = 'Yes' if location[field] else 'No'
                                                    else:
                                                        value = location[field]
                                                        if value:
                                                            value = value.replace('|','/')
                                                            if not len(value):
                                                                value = 'Unavailable'
                                                        else:
                                                            value = ' - '
                                                    message += f"| {value} "
                                            message += '|\n'
                                            if len(uploads)<10:
                                                if 'screen' in location:
                                                    filename = group+'-'+location['fqdn']+'-'+location['lastscrape'].split(' ')[0]+'.png'
                                                    png = base64.b64decode(location['screen'])
                                                    uploads.append({'filename': filename, 'bytes': png})
                                        message += "\n\n"
                                        if len(posts):
                                            count = 1
                                            fields = collections.OrderedDict({
                                                'post_title': 'Title',
                                                'description': 'Description',
                                                'discovered': 'Timestamp',
                                            })
                                            for field in fields:
                                                message += f"| {fields[field]} "
                                            message += '|\n'
                                            for field in fields:
                                                if field in ('post_title', 'description'):
                                                    message += f"| :- "
                                                else:
                                                    message += f"| -: "
                                            message += '|\n'
                                            for post in posts:
                                                if count > limit:
                                                    break
                                                for field in fields:
                                                    if field in post:
                                                        value = post[field].replace('|','/')
                                                        if not len(value):
                                                            value = 'Unavailable'
                                                        message += f"| {value} "
                                                    else:
                                                        message += f'| - '
                                                count += 1
                                                message += '|\n'
                                if len(uploads):
                                    messages.append({'text': message, 'uploads': uploads})
                                else:
                                    messages.append({'text': message})
                else:
                    message = 'Please specify a (partial) group name to query!'
                    messages.append({'text': message})
            if querytype == 'groups':
                endpoint = settings.APIURL['ransomlook']['url']+'groups'
                with requests.get(url=endpoint, headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        count = 1
                        message = '**Ransomlook Groups List**\n\n'
                        message += '| Group ' * settings.WIDTH + '|\n'
                        message += '| :- ' * settings.WIDTH + '|\n'
                        for group in sorted(json_response):
                            message += f"| `{group}` "
                            if not count % settings.WIDTH:
                                message += '|\n'
                            count += 1
                        message += '\n\n'
                        messages.append({'text': message})
            if querytype == 'market':
                if query:
                    endpoint = settings.APIURL['ransomlook']['url']+'markets'
                    with requests.get(url=endpoint, headers=headers) as response:
                        json_response = response.json()
                        if len(json_response):
                            candidates = []
                            for market in json_response:
                                if query.lower() in market.lower():
                                    candidates.append(market)
                        if len(candidates)>1:
                            message = 'Please be more specific, as multiple markets match your query: `%s`' % '`, `'.join(candidates)
                            messages.append({'text': message})
                        else:
                            endpoint = settings.APIURL['ransomlook']['url']+f"market/{candidates[0]}"
                            with requests.get(url=endpoint, headers=headers) as response:
                                marketinfo = response.json()[0]
                                if len(response.json())>1:
                                    posts = response.json()[1]
                                if len(marketinfo):
                                    message = f"**Ransomlook Market Information for `{query}`**\n"
                                    message += '\n\n'
                                    meta = marketinfo['meta'] if marketinfo['meta'] else 'N/A'
                                    message += f"**Description:** `{meta}`\n\n"
                                    if 'locations' in marketinfo:
                                        locations = marketinfo['locations']
                                        fields = collections.OrderedDict({
                                            'fqdn': 'FQDN',
                                            'title': 'Title',
                                            'available': 'Active',
                                            'updated': 'Last Update',
                                        })
                                        for field in fields:
                                            message += f"| {fields[field]} "
                                        message += '|\n'
                                        for field in fields:
                                            if field in ('fqdn', 'title'):
                                                message += f"| :- "
                                            else:
                                                message += f"| -: "
                                        message += '|\n'
                                        for location in locations:
                                            for field in fields:
                                                if field in location:
                                                    if field in ('available',):
                                                        value = 'Yes' if location[field] else 'No'
                                                    else:
                                                        value = location[field]
                                                        if value:
                                                            value = value.replace('|','/')
                                                            if not len(value):
                                                                value = 'Unavailable'
                                                        else:
                                                            value = ' - '
                                                    message += f"| {value} "
                                            message += '|\n'
                                            if len(uploads)<10:
                                                if 'screen' in location:
                                                    filename = market+'-'+location['fqdn']+'-'+location['lastscrape'].split(' ')[0]+'.png'
                                                    png = base64.b64decode(location['screen'])
                                                    uploads.append({'filename': filename, 'bytes': png})
                                        message += "\n\n"
                                        if len(posts):
                                            count = 1
                                            fields = collections.OrderedDict({
                                                'post_title': 'Title',
                                                'description': 'Description',
                                                'discovered': 'Timestamp',
                                            })
                                            for field in fields:
                                                message += f"| {fields[field]} "
                                            message += '|\n'
                                            for field in fields:
                                                if field in ('post_title', 'description'):
                                                    message += f"| :- "
                                                else:
                                                    message += f"| -: "
                                            message += '|\n'
                                            for post in posts:
                                                if count > limit:
                                                    break
                                                for field in fields:
                                                    if field in post:
                                                        value = post[field].replace('|','/')
                                                        if not len(value):
                                                            value = 'Unavailable'
                                                        message += f"| {value} "
                                                    else:
                                                        message += f'| - '
                                                count += 1
                                                message += '|\n'
                                if len(uploads):
                                    messages.append({'text': message, 'uploads': uploads})
                                else:
                                    messages.append({'text': message})
                else:
                    message = 'Please specify a (partial) market name to query!'
                    messages.append({'text': message})
            if querytype == 'markets':
                endpoint = settings.APIURL['ransomlook']['url']+'markets'
                with requests.get(url=endpoint, headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        count = 1
                        message = '**Ransomlook Markets List**\n\n'
                        message += '| Market ' * settings.WIDTH + '|\n'
                        message += '| :- ' * settings.WIDTH + '|\n'
                        for market in sorted(json_response):
                            message += f"| `{market}` "
                            if not count % settings.WIDTH:
                                message += '|\n'
                            count += 1
                        message += '\n\n'
                        messages.append({'text': message})
            if querytype == 'posts':
                endpoint = settings.APIURL['ransomlook']['url']+f"recent/{limit}"
                filter = None
                if query:
                    filter = query
                with requests.get(url=endpoint, headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        count = 1
                        if filter:
                            message = f"**Ransomlook Posts matching `{filter}`** - Last `{limit}` entries\n\n"
                        else:
                            message = f"**Ransomlook Posts** - Last `{limit}` entries\n\n"
                        fields = collections.OrderedDict({
                            'discovered': 'Timestamp',
                            'group_name': 'Group',
                            'post_title': 'Title',
                            'description': 'Description',
                            'screen': 'Screenshot',
                        })
                        for field in fields:
                            message += f"| {fields[field]} "
                        message += '|\n'
                        message += "| :- " * len(fields) + "|\n"
                        count = 1
                        content = False
                        for post in json_response:
                            messageline = ""
                            if count < limit:
                                for field in fields:
                                    value = None
                                    if field in post:
                                        if post[field]:
                                            if field == 'screen':
                                                url = settings.APIURL['ransomlook']['url'].replace('/api','')+post[field]
                                                desc = urllib.parse.unquote_plus(post[field].split('/')[-1])
                                                value = f"[{desc}]({url})"
                                            else:
                                                value = regex.sub(' ', urllib.parse.unquote_plus(post[field].replace('`','')))
                                            if len(value)>400:
                                                value = value[:396] + ' ...'
                                        else:
                                            value = 'N/A'
                                    else:
                                        value = 'N/A'
                                    if field in ('group_name', 'post_title', 'description'):
                                        value = '`'+value+'`'
                                    messageline += f"| {value} "
                            else:
                                break
                            messageline += '|\n'
                            if filter:
                                if filter.lower() in messageline.lower():
                                    message += messageline
                                    content = True
                            else:
                                message += messageline
                                content = True
                            count += 1
                        message += '\n\n'
                        if content:
                            messages.append({'text': message})
            if querytype == 'tgchannels':
                endpoint = settings.APIURL['ransomlook']['url']+'telegram/channels'
                with requests.get(url=endpoint, headers=headers) as response:
                    json_response = response.json()
                    if len(json_response):
                        count = 1
                        message = '**Ransomlook Telegram Channels List**\n\n'
                        message += '| Channel ' * settings.WIDTH + '|\n'
                        message += '| :- ' * settings.WIDTH + '|\n'
                        for tgchannel in sorted(json_response):
                            message += f"| `{tgchannel}` "
                            if not count % settings.WIDTH:
                                message += '|\n'
                            count += 1
                        message += '\n\n'
                        messages.append({'text': message})
            if querytype == 'tgmessages':
                if query:
                    endpoint = settings.APIURL['ransomlook']['url']+'telegram/channels'
                    content = False
                    filter = None
                    candidates = []
                    searches = [query]
                    query = query.split(' ')
                    if len(query)>1:
                        filter = query[-1]
                        searches.append(' '.join(query[:-1]))
                    else:
                        filter = None
                    with requests.get(url=endpoint, headers=headers) as response:
                        json_response = response.json()
                        if len(json_response):
                            for tgchannel in json_response:
                                for search in searches:
                                    if search.lower() in tgchannel.lower():
                                        candidates.append(tgchannel)
                        if len(candidates)>1:
                            message = 'Please be more specific, as multiple Telegram channels match your query: `%s`' % '`, `'.join(candidates)
                            messages.append({'text': message})
                        if len(candidates):
                            endpoint = settings.APIURL['ransomlook']['url']+f"telegram/channel/{candidates[0]}"
                            with requests.get(url=endpoint, headers=headers) as response:
                                json_response = response.json()
                                if len(json_response):
                                    tgchannelinfo = json_response[0]
                                    if len(response.json())>1:
                                        tgmessages = json_response[1]
                                    if len(tgchannelinfo):
                                        if filter:
                                            message = f"**Ransomlook Telegram `{candidates[0]}` Channel Messages matching `{filter}` (Last `{limit}` entries)**\n"
                                        else:
                                            message = f"**Ransomlook Telegram `{candidates[0]}` Channel Messages (Last `{limit}` entries)**\n"
                                        meta = tgchannelinfo['meta'] if tgchannelinfo['meta'] else 'N/A'
                                        link = tgchannelinfo['link'] if tgchannelinfo['link'] else 'N/A'
                                        message += f"**Description:** `{meta}`\n**Link:** `{link}`\n\n"
                                        if len(tgmessages):
                                            count = 1
                                            message += "| Timestamp | Message | Image |\n"
                                            message += "| :- | :- | :- |\n"
                                            for tgmessage in sorted(tgmessages, reverse=True):
                                                if count > limit:
                                                    break
                                                timestamp = tgmessage
                                                if not 'message' in tgmessages[tgmessage]:
                                                    break
                                                msg = tgmessages[tgmessage]['message'] if tgmessages[tgmessage]['message'] else None
                                                if msg:
                                                    msg = regex.sub(' ', msg)
                                                images = tgmessages[tgmessage]['image'] if len(tgmessages[tgmessage]['image']) else []
                                                if filter:
                                                    if msg:
                                                        if not filter.lower() in msg.lower():
                                                            continue
                                                    else:
                                                        continue
                                                if msg or len(images):
                                                    if not len(images):
                                                        imagelist = '-'
                                                    else:
                                                        imagelist = '`, `'.join(images)
                                                    message += f"| {timestamp} | `{msg}` | `{imagelist}` |\n"
                                                    content = True
                                                    for image in images:
                                                        imageurl = settings.APIURL['ransomlook']['url']+f"telegram/channel/{candidates[0]}/image/%s" % (urllib.parse.quote_plus(image,))
                                                        with requests.get(url=imageurl, headers=headers) as image:
                                                            for header in image.headers:
                                                                if header.lower() == 'content-disposition':
                                                                    filename = urllib.parse.unquote_plus(re.findall('filename=(.+)', image.headers[header], re.IGNORECASE)[0]).replace('?','-').replace('"','')
                                                                    bytes = image.content
                                                                    if len(uploads)<10:
                                                                        uploads.append({'filename': filename, 'bytes': bytes})
                                                count += 1
                                            message += '\n\n'
                                    if content:
                                        if len(uploads):
                                            messages.append({'text': message, 'uploads': uploads})
                                        else:
                                            messages.append({'text': message})
                else:
                    message = 'Please specify a (partial) group name to query!'
                    messages.append({'text': message})
        else:
            messages.append({'text': f"RansomLook module does not understand type/query: {querytype}/{query}"})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching the RansomLook API: `%s`\n```%s```\n' % (str(e), traceback.format_exc())})
    finally:
        return {'messages': messages}
