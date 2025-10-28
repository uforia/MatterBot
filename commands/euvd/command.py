#!/usr/bin/env python3

import datetime
import re
import requests
import sys
import traceback
from pathlib import Path
try:
    from commands.euvd import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/euvd/settings.py').is_file():
        try:
            from commands.euvd import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    querytypes = ('euvd', 'search')
    headers = {
        'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for ENISA EUVD v1.0',
    }
    try:
        if len(params) == 0:
            messages.append({'text': 'EUVD: you need to specify one of `%s`!' % ('`, `'.join(querytypes),)})
        else:
            querytype = params[0].lower()
            if not querytype in querytypes:
                messages.append({'text': 'EUVD: you need to specify one of `%s`!' % ('`, `'.join(querytypes),)})
            else:
                if len(params) < 2:
                    messages.append({'text': 'EUVD: you need to specify something to look up!'})
                else:
                    params = params[1:]
                    keywords = []
                    euvds = []
                    if querytype == 'search':
                        severity = ''
                        for param in params:
                            if 'cvss:' in param:
                                severity = param.split('cvss:')[1:][0].lower().split(' ')[0]
                            else:
                                keywords.append(param)
                        if not len(keywords):
                            messages.append({'text': 'EUVD: you need to specify something to look up!'})
                        else:
                            session = requests.Session()
                            url = settings.APIURL['euvd']['url']+'search?text=%s&size=100' % ('%20'.join(keywords),)
                            json_response = None
                            count = 0
                            page = 1
                            while True:
                                if len(severity):
                                    if severity in settings.SEVERITIES:
                                        url += '&fromScore=%s' % settings.SEVERITIES[severity]
                                with session.get(url, headers=headers) as response:
                                    if response.status_code == 200:
                                        json_response = response.json()
                                        if 'items' in json_response:
                                            total = json_response['total']
                                            for euvddetails in json_response['items']:
                                                id = euvddetails['id']
                                                creation = euvddetails['datePublished']
                                                updated = euvddetails['dateUpdated']
                                                desc = regex.sub('',euvddetails['description'])
                                                epss = euvddetails['epss']
                                                cvss = euvddetails['baseScore']
                                                euvds.append({
                                                    'EUVD ID': id,
                                                    'Created At': creation,
                                                    'Last Update': updated,
                                                    'Description': desc,
                                                    'CVSS': cvss,
                                                    'EPSS': str(epss)+'%',
                                                    'URL': 'https://euvd.enisa.europa.eu/vulnerability/%s' % (id,)
                                                })
                                if count < total:
                                    url = settings.APIURL['euvd']['url']+'search?text=%s&size=100&page=%d' % ('%20'.join(keywords), page)
                                    count += 100
                                    page += 1
                                else:
                                    break
                    if querytype == 'euvd':
                        euvd = params[0].lower()
                        if not 'euvd-' in euvd.lower():
                            euvd = 'EUVD-'+euvd
                        euvd = euvd.upper()
                        url = settings.APIURL['euvd']['url']+'enisaid?id=%s' % (euvd,)
                        session = requests.Session()
                        with session.get(url, headers=headers) as response:
                            if response.status_code == 200:
                                euvddetails = response.json()
                                cvss = 0.0
                                vector = 'N/A'
                                id = euvddetails['id']
                                creation = euvddetails['datePublished']
                                updated = euvddetails['dateUpdated']
                                desc = regex.sub('',euvddetails['description'])
                                epss = euvddetails['epss']
                                cvss = euvddetails['baseScore']
                                euvds.append({
                                    'EUVD ID': id,
                                    'Created At': creation,
                                    'Last Update': updated,
                                    'Description': desc,
                                    'CVSS': cvss,
                                    'EPSS': str(epss)+'%',
                                    'URL': 'https://euvd.enisa.europa.eu/vulnerability/%s' % (id,)
                                })
                            else:
                                messages.append({'text': 'The specified EUVD `%s` could not be found.' % (euvd,)})
                    if len(euvds):
                        euvds = sorted(euvds, key=lambda v: v['EUVD ID'], reverse=True)
                        count = 0
                        fields = ('EUVD ID', 'Description', 'CVSS', 'EPSS', 'Created At', 'Last Update')
                        if len(euvds)>10:
                            text = '**EUVD results for `%s %s`: %d found, displaying newest 10**\n' % (querytype,' '.join(params),len(euvds))
                        else:
                            text = '**EUVD results for `%s %s`: %d found**\n' % (querytype,' '.join(params),len(euvds))
                        text += '\n'
                        for field in fields:
                            text += '| %s ' % (field,)
                        text += '|\n'
                        for field in fields:
                            if field in ('EUVD ID', 'CVSS', 'EPSS', 'Created At', 'Last Update'):
                                text += '| -: '
                            else:
                                text += '| :- '
                        text += '|\n'
                        while count < 10 and count < len(euvds):
                            euvd = euvds[count]
                            for field in fields:
                                if field in ('EUVD ID'):
                                    text += '| [%s](%s) ' % (euvd[field],euvd['URL'])
                                else:
                                    text += '| `%s` ' % (euvd[field],)
                            text += '|\n'
                            count += 1
                        text += '\n\n'
                        if len(euvds)>10:
                            euvdcsv = ''
                            euvdcsv += '"'+'","'.join(fields)+'"\n'
                            for euvd in euvds:
                                for field in fields:
                                    if field in ('EUVD ID'):
                                        euvdcsv += '"=HYPERLINK(""%s"";""%s"")",' % (euvd['URL'],euvd[field])
                                    else:
                                        euvdcsv += '"%s",' % (euvd[field],)
                                euvdcsv = euvdcsv.strip(',')+'\n'
                            messages.append({'text': text, 'uploads': [{'filename': 'euvd-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.csv', 'bytes': euvdcsv}]})
                        else:
                            messages.append({'text': text})
    except:
        messages.append({'text': 'An error occurred in the EUVD module:\nError: `%s`' % (traceback.format_exc(),)})
    finally:
        return {'messages': messages}
