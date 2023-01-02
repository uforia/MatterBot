#!/usr/bin/env python3

import httpx
import json
import re
from pathlib import Path
try:
    from commands.ripewhois import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/ripewhois/settings.py').is_file():
        try:
            from commands.ripewhois import settings
        except ModuleNotFoundError: # local test run
            import settings

async def process(connection, channel, username, params):
    if len(params)>0:
        params = params[0]
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        try:
            data = None
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", params):
                data = params.split(':')[0]
            if data:
                async with httpx.AsyncClient() as session:
                    response = await session.get(settings.APIURL['ripewhois']['url'] + data)
                    json_response = response.json()
                    message = 'RIPE WHOIS lookup for `%s`' % data
                    if 'status' in json_response:
                        if json_response['status'] == 'error':
                            return "RIPE WHOIS errored out while searching for `%s`" % (params,)
                    elif 'data' in json_response:
                        data = json_response['data']
                        ranges = set()
                        orgs = set()
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
                                                countries.add(value)
                        orgs = orgs if len(orgs) > 0 else ["Unknown"]
                        ranges = ranges if len(ranges) > 0 else ["Unknown"]
                        countries = orgs if len(countries) > 0 else ["Unknown"]
                        message += ' | Orgs: `' + '`, `'.join(orgs) + '`'
                        message += ' | CIDR: `' + '`, `'.join(ranges) + '`'
                        message += ' | Geo: `' + '`, `'.join(countries) + '`'
                        return message.strip()
                    else:
                        return 'RIPE WHOIS search for `%s` returned no results.' % (params,)
        except Exception as e:
            return "An error occurred searching for `%s`:\nError: `%s`" % (params, e.message)
