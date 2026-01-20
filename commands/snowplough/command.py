#!/usr/bin/env python3

import base64
import requests
import traceback

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
