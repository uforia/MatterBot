#!/usr/bin/env python3

import httpx
import json
import re
from pathlib import Path
try:
    from commands.ipwhois import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/ipwhois/settings.py').is_file():
        try:
            from commands.ipwhois import settings
        except ModuleNotFoundError: # local test run
            import settings

async def process(connection, channel, username, params):
    if len(params)>0:
        params = params[0]
        try:
            data = None
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", params):
                data = params.split(':')[0]
            if data:
                async with httpx.AsyncClient() as session:
                    response = await session.get(settings.APIURL['ipwhois']['url'] + data)
                    json_response = response.json()
                    message = 'IPWHOIS lookup for `%s`' % (data,)
                    if 'success' in json_response:
                        if json_response['success'] != True:
                            return ("IPWHOIS errored out while searching for `%s`" % (params,),)
                        if 'connection' in json_response:
                            if 'isp' in json_response['connection']:
                                message += ' | ISP: `' + json_response['connection']['isp'] + '`'
                            if 'asn' in json_response['connection']:
                                asn = json_response['connection']['asn']
                                if asn != 0:
                                    message += ', ASN `' + str(asn) + '`'
                        if 'city' in json_response:
                            message += ' | Geo: `' + json_response['city'] + '`'
                        if 'country' in json_response:
                            message += ', `' + json_response['country'] + '`'
                        if 'flag' in json_response:
                            if 'emoji' in json_response['flag']:
                                message += ' ' + json_response['flag']['emoji']
                        if 'continent' in json_response:
                                message += ', `' + json_response['continent'] + '`'
                        return {'messages': [
                            {'text': message.strip()},
                        ]}
                    else:
                        return {'messages': [
                            {'text': 'IPWHOIS search for `%s` returned no results.' % (params,)},
                        ]}
        except Exception as e:
            return {'messages': [
                {'text': "An error occurred searching IPWHOIS for `%s`:\nError: `%s`" % (params, e.message)},
            ]}
