#!/usr/bin/env python3

import json
import re
import requests
import traceback

from pathlib import Path
try:
    from commands.asnwhois import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/asnwhois/settings.py').is_file():
        try:
            from commands.asnwhois import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        params = params[0]
        try:
            data = None
            if re.search(r"^[0-9]+$", params):
                data = params
            if data:
                headers = {
                    'Content-Type': settings.CONTENTTYPE,
                    'User-Agent': 'MatterBot integration for ASNWHOIS v0.1'
                }
                url = settings.APIURL['asnwhois']['url']+f"{data}"
                with requests.get(settings.APIURL['asnwhois']['url']+f"{data}", headers=headers) as response:
                    json_response = response.json()
                    message = 'ASN WHOIS lookup for `%s`: ' % (data,)
                    if 'data' in json_response:
                        if json_response['data']['asn'] == None:
                            return {'messages': [
                                {'text': 'ASN `%s` does not exist.' % (data,)}
                            ]}
                        else:
                            jsondata = json_response['data']['asn']
                            name = jsondata['asnName']
                            source = jsondata['source']
                            country = jsondata['country']['iso']
                            peers = str(jsondata['asnDegree']['peer'])
                            providers = str(jsondata['asnDegree']['provider'])
                            lat = str(jsondata['latitude'])
                            long = str(jsondata['longitude'])
                            gpsurl = settings.APIURL['osmdata']['url']+f"lat={lat}&lon={long}&format=json"
                            with requests.get(gpsurl, headers=headers) as response:
                                json_response = response.json()
                                if 'display_name' in json_response:
                                    address = json_response['display_name']
                                else:
                                    address = 'unknown'
                            message += 'Name: `'+name+'`, Address: `'+address+'`, Latitude/Longitude: `'+lat+'`/`'+long+'` :flag-'+country.lower()+':, Peers/Providers: `'+peers+'`/`'+providers+'`, Source: `'+source+'`'
                            return {'messages': [
                                {'text': message.strip()},
                            ]}
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred in GTFOBins:\nError: ' + (str(e),traceback.format_exc())}
            ]}
