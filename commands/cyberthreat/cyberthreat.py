#!/usr/bin/env python3
import os
import requests
import logging
from time import sleep
from . import settings

"""
Util section
"""

def getapikey(*args, **kwargs) -> str :
    try:
        return os.environ.get('CYBERTHREAT_APIKEY', settings.APIURL['cyberthreat']['apikey'])
    except:
        raise Exception("Could not get token. API key should be supplied in the variable CYBERTHREAT_APIKEY or in settings.py")


def wget(url: str) -> dict:
    """
    wget is a default way to get information from the cyberthreat API. Provide a full path to an API endpoint, starting with a /.
    Returns json.
    """

    if url.startswith(('http://', 'https://')):
        pass
    elif url.startswith(('api/v2', '/api/v2')):
        raise ValueError('api path should be in the settings file and not duplicated here.')
    else:
        url = settings.APIURL['cyberthreat']['url']+url

    try:
        headers =  {"Content-Type":"application/json",
                    "Accept": "application/json",
                    "Authorization": f'Token {getapikey()}'}

        logging.debug(f"GET: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code >= 500:
            logging.info("Error. Sleeping for 5 seconds.")
            sleep(5)
            response = requests.get(url, headers=headers)

    except requests.exceptions.Timeout:
        raise Exception('Timeout')
    except requests.exceptions.TooManyRedirects:
        raise Exception('Too many redirects!')

    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        raise Exception(f'Connection error!\n{e}')

    else:
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Response code {response.status_code}\n{response.text}')### Dynamic configuration loader (do not change/edit)
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