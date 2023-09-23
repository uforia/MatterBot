#!/usr/bin/env python3

import base64
import requests
import traceback
from pathlib import Path
try:
    from commands.snowplough import defaults as settings
except ModuleNotFoundError:
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/snowplough/settings.py').is_file():
        try:
            from commands.snowplough import settings
        except ModuleNotFoundError:
            import settings


def process(command, channel, username, params, files, conn):
    if len(params)>0:
        messages = []
        params = params[0].replace('[.]','.')
        token = base64.b64encode(f"{settings.APIURL['servicenow']['username']}:{settings.APIURL['servicenow']['password']}".encode('utf-8')).decode('ascii')
        print(token)
        url = settings.APIURL['servicenow']['url']
        try:
            headers = {
                'Content-Type': settings.CONTENTTYPE,
                'Authorization': 'Basic %s' % (token,),
            }
            print(headers)
            print(url)
            with requests.get(url, headers=headers) as response:
                json_response = response.json()
                print(json_response)
        except Exception as e:
            messages.append({'text': "An error occurred searching ServiceNow:`%s`\nError: %s" % (str(e),traceback.format_exc())})
        finally:
            print(messages)
            return {'messages': messages}
