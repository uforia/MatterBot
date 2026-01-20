#!/usr/bin/env python3

import base64
import requests
import traceback

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
