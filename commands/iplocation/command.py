#!/usr/bin/env python3

import json
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.iplocation import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/iplocation/settings.py').is_file():
        try:
            from commands.iplocation import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        try:
            messages = []
            ip = params[0]
            if not re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", ip) and \
               not re.search(r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", ip):
                return
            else:
                with requests.get(settings.APIURL['iplocation']['url']+ip) as response:
                    data = response.json()
                    message = f'**IPLocation lookup for {ip}**\n\n'
                    fieldmap = {
                        'ip': 'IP Address',
                        'country_code2': 'Country',
                        'isp': 'ISP',
                    }
                    for field in fieldmap:
                        message += f'| {fieldmap[field]} '
                    message += '|\n'
                    for field in fieldmap:
                        if field in ('ip','country_code2'):
                            message += '| -: '
                        else:
                            message += '| :- '
                    message += '|\n'
                    for field in fieldmap:
                        value = data[field]
                        if field == 'country_code2':
                            message += f'| :flag-{value}: '
                        else:
                            message += f'| {value} '
                    message += '|\n'
                    message += '\n\n'
                    messages.append({'text': message})
        except Exception as e:
            messages.append({'text': 'A Python error occurred searching the IPLocation API: `%s`\n```%s```\n' % (str(e), traceback.format_exc())})
        finally:
            return {'messages': messages}