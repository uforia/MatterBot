#!/usr/bin/env python3

import re
import requests

### Dynamic configuration loader (do not change/edit)
import importlib
from pathlib import Path
_pkg_name = Path(__file__).parent.name
try:
    defaults_mod = importlib.import_module(f'commands.{_pkg_name}.defaults')
except ModuleNotFoundError:
    try:
        defaults_mod = importlib.import_module('defaults')
    except ModuleNotFoundError:
        print(f"Module {_pkg_name} could not be loaded due to a missing default configuration.")
try:
    settings_mod = importlib.import_module(f'commands.{_pkg_name}.settings')
except ModuleNotFoundError:
    try:
        settings_mod = importlib.import_module('settings')
    except ModuleNotFoundError:
        settings_mod = None
settings = {k: v for k, v in vars(defaults_mod).items() if not k.startswith('__')}
if settings_mod:
    settings.update({k: v for k, v in vars(settings_mod).items() if not k.startswith('__')})
from types import SimpleNamespace
settings = SimpleNamespace(**settings)
### Loader end, actual module functionality starts here

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
