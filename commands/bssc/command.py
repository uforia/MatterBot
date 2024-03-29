#!/usr/bin/env python3

import re
import requests
import traceback
from pathlib import Path
try:
    from commands.bssc import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/bssc/settings.py').is_file():
        try:
            from commands.bssc import settings
        except ModuleNotFoundError: # local test run
            import settings


def getToken():
    auth = {
        'Authorization': 'Basic %s' % settings.APIURL['bssc']['key'],
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    try:
        with requests.post(settings.APIURL['bssc']['token'], headers=auth) as response:
            json_response = response.json()
            if 'access_token' in json_response and 'token_type' in json_response:
                return json_response['access_token']
            else:
                return None
    except:
        return None

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        messages = []
        params = params[0].replace('[.]','.')
        try:
            endpoint = None
            # IP address, domain or URL?
            if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", params) or \
               re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", params) or \
               params.startswith('http'):
                endpoint = settings.APIURL['bssc']['url'] + '/network/%s' % (params,)
            elif re.search(r"^[A-Fa-f0-9]{64}$", params):
                # SHA256 hash?
                endpoint = settings.APIURL['bssc']['url'] + '/file/%s' % (params,)
            if endpoint:
                message = '\n| **Broadcom Symantec Security Cloud** | `%s` |' % (params,)
                message += '\n| :- | :- |'
                if (token := getToken()):
                    outputFields = {
                        'threatRiskLevel': 'Threat Risk Level',
                        'categorization': 'Categories',
                        'firstSeen': 'First Seen',
                        'lastSeen': 'Last Seen',
                        'reputation': 'Reputation',
                        'prevalence': 'Prevalence',
                        'targetOrgs': 'Targeted Organizations',
                        'actors': 'Threat Actors',
                        'associatedReferences': 'Associated References',
                    }
                    headers = {
                        'Authorization': 'Bearer %s' % token,
                        'Content-Type': settings.CONTENTTYPE,
                    }
                    with requests.get(endpoint, headers=headers) as response:
                        data = ''
                        json_response = response.json()
                        for outputField in outputFields.keys():
                            if outputField in json_response:
                                if outputField == 'threatRiskLevel':
                                    data += '\n| '+outputFields[outputField]+' | `'+str(json_response[outputField]['level'])+'` |'
                                elif outputField == 'targetOrgs':
                                    if 'topCountries' in json_response['targetOrgs']:
                                        if len(json_response['targetOrgs']['topCountries']):
                                            topCountries = [_ for _ in json_response['targetOrgs']['topCountries'] if _]
                                            if len(topCountries):
                                                data += '\n| Top Targeted Countries |'
                                                for topCountry in topCountries:
                                                    data += ' :flag-%s:' % (topCountry,)
                                                data += ' |'
                                    if 'topIndustries' in json_response['targetOrgs']:
                                        if len(json_response['targetOrgs']['topIndustries']):
                                            topIndustries = [_ for _ in json_response['targetOrgs']['topIndustries'] if _]
                                            if len(topIndustries):
                                                data += '\n| Top Targeted Industries | `'+'`, `'.join(topIndustries)+'` |'
                                elif outputField == 'categorization':
                                    data += '\n| Categories | '
                                    for category in json_response['categorization']['categories']:
                                        data += '`'+category['name']+' ('+str(category['id'])+')`, '
                                    data = data[:-2]
                                    data += ' |'
                                elif outputField == 'actors':
                                    data += '\n| Associated Threat Actors | `'+'`, `'.join(json_response['actors'])+'` |'
                                elif outputField == 'associatedReferences':
                                    for associatedReference in json_response['associatedReferences']:
                                        data += '\n| Associated Reference | ['+associatedReference['description']+'] |'
                                        data += '('+associatedReference['url']+')'
                                else:
                                    data += '\n| '+outputFields[outputField]+' | `'+json_response[outputField]+'` |'
                        if len(data):
                            message += data
                            message += '\n\n'
                            messages.append({'text': message})
        except Exception as e:
            messages.append({'text': "An error occurred searching Broadcom Symantec Security Cloud:`%s`\nError: %s" % (str(e),traceback.format_exc())})
        finally:
            return {'messages': messages}
