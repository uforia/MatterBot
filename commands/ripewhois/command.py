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
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http')
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        try:
            data = None
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", params):
                data = params.split(':')[0]
            if data:
                with requests.get(settings.APIURL['ripewhois']['url'] + data) as response:
                    json_response = response.json()
                    message = 'RIPE WHOIS lookup for `%s`' % (params,)
                    if 'status' in json_response:
                        if json_response['status'] == 'error':
                            return {'messages': [
                                {'text': 'RIPE WHOIS errored out while searching for `%s`' % (params,)}
                            ]}
                    if 'data' in json_response:
                        data = json_response['data']
                        orgs = set()
                        ranges = set()
                        countries = set()
                        for subtree in ['records', 'irr_records']:
                            if subtree in data:
                                records = data[subtree]
                                for record in records:
                                    for entry in record:
                                        key = entry['key']
                                        values = entry['value']
                                        if key == 'inetnum' or key == 'NetRange':
                                            values = values.split(', ')
                                            for value in values:
                                                ranges.add(value)
                                        if key == 'descr' or key == 'OrgName' or key == 'netname':
                                            values = values.split(', ')
                                            for value in values:
                                                orgs.add(value)
                                        if key == 'country':
                                            values = values.split(', ')
                                            for value in values:
                                                countries.add('`' + value + '` :flag-' + value.lower() + ':')
                        orgs = orgs if len(orgs) > 0 else ["Unknown"]
                        ranges = ranges if len(ranges) > 0 else ["Unknown"]
                        countries = countries if len(countries) > 0 else ["`Unknown`"]
                        message += ' | Orgs: `' + '`, `'.join(orgs) + '`'
                        message += ' | CIDR: `' + '`, `'.join(ranges) + '`'
                        message += ' | Geo: ' + ', '.join(countries)
                        return {'messages': [
                            {'text': message.strip()}
                        ]}
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred searching RIPE WHOIS:\nError: ' + str(e)}
            ]}
