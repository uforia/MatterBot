#!/usr/bin/env python3

import json
import re
import requests
from pathlib import Path
try:
    from commands.geolookup import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/geolookup/settings.py').is_file():
        try:
            from commands.geolookup import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        try:
            headers = {
                'User-Agent': 'MatterBot integration for Geolookup v0.1',
            }
            if len(params)<2:
                message = 'Geolookup: specify a valid latitude/longitude!'
            else:
                lat = params[0]
                long = params[1]
                if re.search(r"^[\-\.0-9]+$", lat) and re.search(r"^[\-\.0-9]+$", long):
                    # Close enough
                    with requests.get(settings.APIURL['osmdata']['url']+'lat='+lat+'&lon='+long+'&format=json', headers=headers) as response:
                        json_response = response.json()
                        message = 'Geographical address lookup for latitude `%s`, longitude `%s`: ' % (lat, long)
                        if 'display_name' in json_response:
                            address = json_response['display_name']
                        else:
                            address = 'unknown'
                        message += '`'+address+'`'
                else:
                    message = 'Geolookup: not a valid latitude/longitude!'
            return {'messages': [
                {'text': message.strip()},
            ]}
        except Exception as e:
            return {'messages': [
                {'text': "Geolookup: An error occurred during geolookup: `%s`" % (str(e),)},
            ]}
