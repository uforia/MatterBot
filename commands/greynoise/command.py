#!/usr/bin/env python3

import datetime
import math
import random
import re
import requests
import traceback
import urllib.parse
from pathlib import Path
try:
    from commands.greynoise import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/greynoise/settings.py').is_file():
        try:
            from commands.greynoise import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(settings.APIURL['greynoise']['key']):
        apikey = random.choice(settings.APIURL['greynoise']['key'])
    else:
        return
    # Methods to query the current API account info (credits etc.)
    querytypes = {
        'community':    '/v3/community/',
        'ipcontext':    '/v2/noise/context/',
        'ipquick':      '/v2/noise/quick/',
        'riot':         '/v2/riot/',
        'gnql':         '/v2/experimental/gnql',
        'gnqlstats':    '/v2/experimental/gnql/stats',
        'timeline':     '/v3/noise/ips/',
        'similarity':   '/v3/similarity/ips/',
        'ping':         '/ping',
    }
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    try:
        if len(params)>0:
            querytype = params[0] if params[0] in querytypes else 'community'
            if not querytype in querytypes:
                return
            APIENDPOINT = settings.APIURL['greynoise']['url']
            headers = {
                'accept':   settings.CONTENTTYPE,
                'key':      apikey,
            }
            if querytype == 'ping':
                APIENDPOINT += querytypes[querytype]
                with requests.get(APIENDPOINT, headers=headers) as response:
                    json_response = response.json()
                    if 'message' in json_response:
                        if json_response['message'] == 'pong':
                            expiration = json_response['expiration']
                            offering = json_response['offering']
                            message =  '\n| GreyNoise | Account Information |'
                            message += '\n| :- | -: |'
                            message += '\n| **Offering** | `%s` |' % (offering,)
                            message += '\n| **Expiration** | `%s` |' % (expiration,)
                            message += '\n\n'
                            messages.append({'text': message})
            else:
                if len(params)>1:
                    query = params[1:]
                    if querytype == 'community':
                        pass
                    if querytype == 'ipcontext':
                        pass
                    if querytype == 'ipquick':
                        pass
                    if querytype == 'riot':
                        pass
                    if querytype == 'gnql':
                        pass
                    if querytype == 'gnqlstats':
                        pass
                    if querytype == 'timeline':
                        pass
                    if querytype == 'similarity':
                        pass
                else:
                    query = params[0]
                    if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", query) or \
                       re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", query):
                        querytype = 'community'
                        APIENDPOINT += urllib.parse.quote(querytypes[querytype]+'%s' % (query,))
                        with requests.get(APIENDPOINT, headers=headers) as response:
                            json_response = response.json()
                            if response.status_code == 200:
                                fields = {
                                    'ip': 'IP Address',
                                    'noise': 'Noise',
                                    'riot': 'RIOT',
                                    'message': 'Context',
                                }
                                for field in fields:
                                    print(field)
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching GreyNoise:\nError: `%s`' % (traceback.format_exc(),)})
    finally:
        return {'messages': messages}
