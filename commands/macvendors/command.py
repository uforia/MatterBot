#!/usr/bin/env python3

import requests
import traceback
import urllib.parse
import re

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

def isMac (address): # Check if param is valid mac addr format
    patterns = [
        r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',   # 00:11:22:33:44:55 or 00-11-22-33-44-55
        r'^([0-9A-Fa-f]{2}\.){5}([0-9A-Fa-f]{2})$',     # 00.11.22.33.44.55
        r'^[0-9A-Fa-f]{12}$',                           # 001122334455
        r'^([0-9A-Fa-f]{4}\.){2}([0-9A-Fa-f]{4})$',     # 0011.2233.4455
    ]
    for pattern in patterns:
        if re.match(pattern, address):
            return True
    return False

def process(command, channel, username, params, files, conn):

    if not params:
        return {'messages': [{'text': "No parameters provided."}]}
    address = params[0]

    try:
        messages = []
        if not isMac(address):
            return messages.append({'text': f"`{address}` is not a valid address format"})
        api_url = f"{settings.APIURL['macvendors']['url']}{urllib.parse.quote(address)}"         # API URL for fetching data
        response = requests.get(api_url)
        if response.status_code == 200:
            messages.append({'text': f"Vendor: `{response.text}`"})
        else:
            messages.append({'text': "Vendor not found"})
    except requests.exceptions.RequestException as e:
        if response.status_code == 429:
            messages.append({'text': f"Rate limit exceeded."})
        else:    
            # Handle HTTP request errors
            messages.append({'text': f"An HTTP error occurred querying MACVendors:\nError: {str(e)}\n{traceback.format_exc()}"})
    except Exception as e:
        # Catch other unexpected errors
        messages.append({'text': f"An error occurred querying MACVendors:\nError: {str(e)}\n{traceback.format_exc()}"})
    finally:
        return {'messages': messages}