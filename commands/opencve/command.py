#!/usr/bin/env python3

import collections
import datetime
import math
import random
import re
import requests
import traceback
import urllib
from pathlib import Path
try:
    from commands.opencve import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/opencve/settings.py').is_file():
        try:
            from commands.opencve import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    headers = {
        'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for ENISA EUVD v1.0',
    }
    querytypes = ('cve', 'search')
    try:
        if len(params) == 0:
            messages.append({'text': 'OpenCVE: you need to specify one of `%s`!' % ('`, `'.join(querytypes),)})
        else:
            querytype = params[0].lower()
            if not querytype in querytypes:
                messages.append({'text': 'OpenCVE: you need to specify one of `%s`!' % ('`, `'.join(querytypes),)})
            else:
                if len(params) < 2:
                    messages.append({'text': 'OpenCVE: you need to specify something to look up!'})
                else:
                    params = params[1:]
                    keywords = []
                    cves = []
                    severities = set()
                    if querytype == 'search':
                        severity = ''
                        for param in params:
                            if 'cvss:' in param:
                                severities.add(param.split('cvss:')[1:][0].lower())
                            else:
                                keywords.append(param)
                        if not len(keywords):
                            messages.append({'text': 'OpenCVE: you need to specify something to look up!'})
                        else:
                            session = requests.Session()
                            session.auth = (settings.APIURL['opencve']['username'],settings.APIURL['opencve']['password'])
                            url = settings.APIURL['opencve']['url']+'/cve?search=%s' % (keywords[0],)
                            json_response = None
                            while True:
                                if len(severities):
                                    url += '&cvss=%s' % ','.join(severities)
                                with session.get(url, headers=headers) as response:
                                    if response.status_code == 200:
                                        json_response = response.json()
                                        for cve in json_response['results']:
                                            id = cve['cve_id']
                                            creation = cve['created_at']
                                            updated = cve['updated_at']
                                            desc = regex.sub('',cve['description'])
                                            vector = None
                                            cveurl = settings.APIURL['opencve']['url']+'/cve/%s' % (id,)
                                            with session.get(cveurl, headers=headers) as response:
                                                cvedetails = response.json()
                                                cvss = 0.0
                                                vector = 'N/A'
                                                for cvssversion in ('cvssV4_0', 'cvssV3_1', 'cvssV3_0', 'cvssV2_0'):
                                                    if cvssversion in cvedetails['metrics']:
                                                        cvssdata = cvedetails['metrics'][cvssversion]
                                                        if len(cvssdata['data']):
                                                            cvss = cvssdata['data']['score']
                                                            vector = cvssdata['data']['vector']
                                                            break
                                            cves.append({
                                                'CVE ID': id,
                                                'Created At': creation,
                                                'Last Update': updated,
                                                'Description': desc,
                                                'CVSS': cvss,
                                                'Vector': vector,
                                                'URL': settings.APIURL['opencve']['url'].replace('/api','')+'/cve/%s' % (id,)
                                            })
                                if 'next' in json_response:
                                    if json_response['next']:
                                        url = json_response['next'].replace('http://', 'https://')
                                    else:
                                        break
                    if querytype == 'cve':
                        cve = params[0].lower()
                        if not 'cve-' in cve:
                            cve = 'CVE-'+cve
                        cve = cve.upper()
                        url = settings.APIURL['opencve']['url']+'/cve/%s' % (cve,)
                        session = requests.Session()
                        session.auth = (settings.APIURL['opencve']['username'],settings.APIURL['opencve']['password'])
                        with session.get(url, headers=headers) as response:
                            if response.status_code == 200:
                                cvedetails = response.json()
                                cvss = 0.0
                                epss = "-"
                                percentile = "-"
                                vector = 'N/A'
                                id = cvedetails['cve_id']
                                creation = cvedetails['created_at']
                                updated = cvedetails['updated_at']
                                desc = regex.sub('',cvedetails['description'])
                                for cvssversion in ('cvssV4_0', 'cvssV3_1', 'cvssV3_0', 'cvssV2_0'):
                                    if cvssversion in cvedetails['metrics']:
                                        cvssdata = cvedetails['metrics'][cvssversion]
                                        if len(cvssdata['data']):
                                            cvss = cvssdata['data']['score']
                                            epssurl = f"https://api.first.org/data/v1/epss?cve={cve}"
                                            with session.get(epssurl, headers=headers) as epssresponse:
                                                if epssresponse.status_code == 200:
                                                    epssdetails = epssresponse.json()
                                                    if 'status-code' in epssdetails:
                                                        if epssdetails['status-code'] == 200:
                                                            epss = str(round(float(epssdetails['data'][0]['epss']),4)*100)+"%"
                                                            percentile = str(round(float(epssdetails['data'][0]['percentile']),4)*100)+"%"
                                            vector = cvssdata['data']['vector']
                                            break
                                cves.append({
                                    'CVE ID': id,
                                    'Created At': creation,
                                    'Last Update': updated,
                                    'Description': desc,
                                    'CVSS': cvss,
                                    'EPSS': epss,
                                    'Percentile': percentile,
                                    'Vector': vector,
                                    'URL': settings.APIURL['opencve']['url'].replace('/api','')+'/cve/%s' % (id,)
                                })
                            else:
                                messages.append({'text': 'The specified CVE `%s` could not be found.' % (cve,)})
                    if len(cves):
                        cves = sorted(cves, key=lambda v: v['Last Update'], reverse=True)
                        count = 0
                        fields = ('CVE ID', 'Description', 'CVSS', 'EPSS', 'Percentile', 'Vector', 'Created At', 'Last Update')
                        if len(cves)>10:
                            text = '**OpenCVE results for `%s %s`: %d found, displaying newest 10**\n' % (querytype,' '.join(params),len(cves))
                        else:
                            text = '**OpenCVE results for `%s %s`: %d found**\n' % (querytype,' '.join(params),len(cves))
                        text += '\n'
                        for field in fields:
                            text += '| %s ' % (field,)
                        text += '|\n'
                        for field in fields:
                            if field in ('CVE ID', 'CVSS', 'EPSS', 'Percentile', 'Created At', 'Last Update'):
                                text += '| -: '
                            else:
                                text += '| :- '
                        text += '|\n'
                        while count < 10 and count < len(cves):
                            cve = cves[count]
                            for field in fields:
                                if field in ('CVE ID',):
                                    text += '| [%s](%s) ' % (cve[field],cve['URL'])
                                else:
                                    if field in cve:
                                        text += '| `%s` ' % (cve[field],)
                                    else:
                                        text += '| `-` '
                            text += '|\n'
                            count += 1
                        text += '\n\n'
                        if len(cves)>10:
                            opencvecsv = ''
                            opencvecsv += '"'+'","'.join(fields)+'"\n'
                            for cve in cves:
                                for field in fields:
                                    if field in ('CVE ID'):
                                        opencvecsv += '"=HYPERLINK(""%s"";""%s"")",' % (cve['URL'],cve[field])
                                    else:
                                        opencvecsv += '"%s",' % (cve[field],)
                                opencvecsv = opencvecsv.strip(',')+'\n'
                            messages.append({'text': text, 'uploads': [{'filename': 'opencve-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.csv', 'bytes': opencvecsv}]})
                        else:
                            messages.append({'text': text})
    except:
        messages.append({'text': 'An error occurred in the OpenCVE module:\nError: `%s`' % (traceback.format_exc(),)})
    finally:
        return {'messages': messages}
