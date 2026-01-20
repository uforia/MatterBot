#!/usr/bin/env python3

import re
import requests

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
