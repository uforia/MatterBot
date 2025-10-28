#!/usr/bin/env python3

import collections
import datetime
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.onionlookup import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/onionlookup/settings.py').is_file():
        try:
            from commands.onionlookup import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http').replace('https://','').replace('http://','')
        stripchars = r'\[\]\n\r\'\"|'
        regex = re.compile('[%s]' % stripchars)
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'User-Agent': 'MatterBot integration for Onion-Lookup API v1.0',
        }
        try:
            messages = []
            if params.endswith('.onion'):
                with requests.get(settings.APIURL['onionlookup']['url']+f"{params}", headers=headers) as response:
                    if response.status_code in (400,401,402,403,):
                        messages.append({'text': "Failed Onion-Lookup, check address validity or try again later ..."})
                    if response.status_code in (200,):
                        json_response = response.json()
                        if isinstance(json_response, list):
                            if 404 in json_response:
                                messages.append({'text': f"Onion domain `{params}` not found!"})
                        else:
                            fields = collections.OrderedDict({
                                'first_seen': 'First Seen',
                                'last_seen': 'Last Seen',
                                'languages': 'Languages',
                                'tags': 'Metadata',
                                'titles': 'Page Titles',
                            })
                            message = f"| Onion-Lookup Results | `{params}` |\n"
                            message += f"| :- | :- |\n"
                            for field in fields:
                                if field in json_response:
                                    if field in ('tags',):
                                        tagcollection = collections.OrderedDict()
                                        for tagentry in json_response[field]:
                                            tagtype = tagentry.split(':')[0]
                                            tag = regex.sub('',tagentry.split('=')[1].replace('"','').replace('-',' ').title())
                                            if not tagtype in tagcollection:
                                                tagcollection[tagtype] = []
                                            if not tag in tagcollection[tagtype]:
                                                tagcollection[tagtype].append(tag)
                                        for tagtype in tagcollection:
                                            message += f"| **Tag**: `{tagtype.title()}` | "
                                            message += "`"+"`, `".join(tagcollection[tagtype])+"`"
                                            message += " |\n"
                                    else:
                                        if field in ('first_seen', 'last_seen'):
                                            try:
                                                datetime_object = datetime.datetime.strptime(json_response[field], "%Y-%m-%d")
                                                result = datetime_object.strftime("%B %d, %Y")
                                            except:
                                                result = json_response[field]
                                        elif field in ('titles',):
                                            result = '`'+'`, `'.join(json_response[field])+'`'
                                        elif field in ('languages',):
                                            result = ' '.join([':flag-'+_+':' for _ in json_response[field]]).replace('flag-en','flag-england')
                                        else:
                                            result = json_response[field]
                                        if len(result):
                                            message += f"| **{fields[field]}** "
                                            message += f"| {regex.sub('',result)} |\n"
                            message += "\n\n"
                            messages.append({'text': message.strip()})
        except Exception as e:
            messages.append({'text': 'A Python error occurred searching onionlookup: %s\n%s' % (str(e),traceback.format_exc())})
        finally:
            return {'messages': messages}