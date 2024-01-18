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
                #return b'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJuZWRlci1hYTIiLCJpc3MiOiJxYXMiLCJwb3J0YWxVc2VySWQiOjE3Mjk0MTAxNywiY3VzdG9tZXJVdWlkIjoiZTA2NjU2NTUtMjMzYy1lOWZjLTgwYTAtYmFhNjc1N2Q5OTE0IiwibW9kdWxlc0FsbG93ZWQiOlsiQVNTRVQgSU5WRU5UT1JZIiwiRUMyIiwiS0JYIiwiUkVQT1JUIENFTlRFUiIsIkFETUlOIiwiQ0VSVFZJRVciLCJDT05USU5VT1VTIE1PTklUT1JJTkciLCJGUkVFIEFHRU5UIiwiU0VDVVJFQ09ORklHIiwiVk0iLCJBU1NFVF9NQU5BR0VNRU5UIiwiUFMiLCJDTE9VRFZJRVciLCJHTE9CQUxfQUlfQ01EQl9TWU5DIiwiUE0iLCJQT1JUQUwgVEFHR0lORyIsIlNDQU4gQlkgSE9TVE5BTUUiLCJTRU0iLCJDT05UQUlORVJfU0VDVVJJVFkiLCJNRFMiLCJRR1MiLCJTQ0FfQUdFTlQiLCJWTEFOIiwiVk0gQUdFTlQiLCJJT0MiLCJJVEFNIiwiUENJIiwiVEhSRUFUIFBST1RFQ1QiLCJUSFJFQVRfUFJPVEVDVCIsIlZJUlRVQUwgU0NBTk5FUiIsIkFQSSIsIkNBIiwiQ0VSVF9WSUVXIiwiQ00iLCJDUyIsIlBBU1NJVkVfU0NBTk5FUiIsIlZNIFNDQU5ORVIiXSwiY3VzdG9tZXJJZCI6ODY4NDY3LCJzZXNzaW9uRXhwaXJhdGlvbiI6IjYwIiwiand0RXhwaXJ5TWludXRlIjoiMjQwIiwiZXhwIjoxNzA1MzI2MDE3LCJpYXQiOjE3MDUzMTE2MTcsImp0aSI6IlRHVDIxOTQxMzEtTWRrRUhvbGxnc0FMWmVZVFJsYkxDYmZLa1V6SmlMZ0xRV2hvbWhERXJaZ3BOYmxKZ0FaYWhoUkR0ZXNaaWxKZC1xYXMtNjg2NmY0Y2M2Yy14Mmd0bSIsImxvZ2luUmVzcG9uc2UiOiJTVUNDRVNTRlVMIiwiYXV0aGVudGljYXRpb25EYXRlIjpbMTcwNTMxMTYxNzg4OF0sInN1Y2Nlc3NmdWxBdXRoZW50aWNhdGlvbkhhbmRsZXJzIjpbIkF1dGhIYW5kbGVyIl0sImlwQWRkcmVzcyI6Ijc3LjE2MS4xNDYuMTY0IiwidXNlcnR5cGUiOiJmbyIsInF3ZWJVc2VySWQiOjkxMjI5NzA1LCJjcmVkZW50aWFsVHlwZSI6IlFVc2VybmFtZVBhc3N3b3JkQ3JlZGVudGlhbCIsImF1ZCI6InFhcyIsImF1dGhlbnRpY2F0aW9uTWV0aG9kIjoiQXV0aEhhbmRsZXIiLCJ1c2VyVXVpZCI6IjlmOTlkYzgzLWUzYjgtZTg2YS04MDY1LTFmMWJiNjFiNDQ2NCIsInN1YnNjcmlwdGlvblV1aWQiOiJlMDY2NTY1NS0yMzNjLWU5ZmMtODBhMC1iYWE2NzU3ZDk5MTQ'
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