#!/usr/bin/env python3

import json
import re
import requests
import sys
import traceback
import urllib.parse
from pathlib import Path
try:
    from commands.qualys import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/qualys/settings.py').is_file():
        try:
            from commands.qualys import settings
        except ModuleNotFoundError: # local test run
            import settings

def getToken():
    try:
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        username = urllib.parse.quote(settings.APIURL['qualys']['username'])
        password = urllib.parse.quote(settings.APIURL['qualys']['password'])
        data = 'username=%s&password=%s&token=true' % (username,password)
        with requests.post(settings.APIURL['qualys']['jwt'], headers=headers, data=data) as response:
            content = response.content.decode()
            if 'Authentication Failure' in content:
                return None
            else:
                return content
    except:
        return None

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    messages = []
    querytypes = ['domain','host','ip','software','sw']
    stripchars = '`\[\]\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    try:
        if len(params)>0:
            querytype = regex.sub('',params[0].lower())
            if querytype not in querytypes:
                return
            if querytype:
                token = getToken()
                if token:
                    headers = {
                        'Accept-Encoding': settings.CONTENTTYPE,
                        'Content-Type': settings.CONTENTTYPE,
                        'Authorization': 'Bearer %s' % (token,),
                    }
                    filtermap = {
                        'domain': {
                            'field': 'asset.domain',
                            'operator': 'CONTAINS',
                        },
                        'ip': {
                            'field': 'interfaces.address',
                            'operator': 'EQUALS',
                        },
                        'host': {
                            'field': 'asset.name',
                            'operator': 'EQUALS',
                        },
                        'software': {
                            'field': 'software.product',
                            'operator': 'CONTAINS',
                        },
                        'sw': {
                            'field': 'software.product',
                            'operator': 'CONTAINS',
                        },
                    }
                    filtermap[querytype]['value'] = params[1]
                    jsonfilter = json.dumps({'filters': [filtermap[querytype]]})
                    print(jsonfilter)
                    print(token)
                    with requests.post(settings.APIURL['qualys']['csam'], headers=headers, data=jsonfilter) as response:
                        print(response.content)
                else:
                    messages.append({'text': 'The Qualys module could not obtain a valid JWT token. Check your credentials and/or subscription permissions.'})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching the Qualys API:%s\n%s' % (str(e), traceback.format_exc())})
    finally:
        return {'messages': messages}

if __name__ == '__main__':
    process('command','channel','username',sys.argv[1:],'files','conn')