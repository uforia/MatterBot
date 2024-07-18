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
    querytypes = ['search', 'cve']
    severities = ['low', 'medium', 'high', 'critical']
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
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
                    if querytype == 'search':
                        severity = None
                        for param in params:
                            if 'cvss:' in param:
                                cvss = param.split('cvss:')[1:][0]
                                if not cvss in severities:
                                    messages.append({'text': 'OpenCVE: `%s` is not one of `%s`!' % (cvss, '`, `'.join(severities))})
                                else:
                                    severity = cvss
                            else:
                                keywords.append(param)
                        if not len(keywords):
                            messages.append({'text': 'OpenCVE: you need to specify something to look up!'})
                        else:
                            page = 1
                            session = requests.Session()
                            session.auth = (settings.APIURL['opencve']['username'],settings.APIURL['opencve']['password'])
                            url = settings.APIURL['opencve']['url']+'/cve?search=%s' % (keywords[0],)
                            if severity:
                                url += '&cvss=%s' % (severity,)
                            while True:
                                urlpage = url+'&page=%d' % (page,)
                                with session.get(urlpage) as response:
                                    if response.status_code == 200:
                                        page += 1
                                        json_response = response.json()
                                        for cve in json_response:
                                            id = cve['id']
                                            creation = cve['created_at']
                                            updated = cve['updated_at']
                                            desc = regex.sub('',cve['summary'])
                                            vector = None
                                            if all(keyword.lower() in desc.lower() for keyword in keywords):
                                                cveurl = settings.APIURL['opencve']['url']+'/cve/%s' % (id,)
                                                with session.get(cveurl) as response:
                                                    cvedetails = response.json()
                                                    if 'v3' in cvedetails['cvss']:
                                                        cvss = cvedetails['cvss']['v3']
                                                        if 'cvssMetricV31' in cvedetails['raw_nvd_data']['metrics']:
                                                            vector = cvedetails['raw_nvd_data']['metrics']['cvssMetricV31'][0]['cvssData']['vectorString']
                                                        elif 'cvssMetricV30' in cvedetails['raw_nvd_data']['metrics']:
                                                            vector = cvedetails['raw_nvd_data']['metrics']['cvssMetricV30'][0]['cvssData']['vectorString']
                                                    elif 'v2' in cvedetails['cvss']:
                                                        cvss = cvedetails['cvss']['v2']
                                                        vector = cvedetails['raw_nvd_data']['metrics']['cvssMetricV2'][0]['cvssData']['vectorString']
                                                    else:
                                                        cvss = 0.0
                                                cves.append({
                                                    'CVE ID': id,
                                                    'Created At': creation,
                                                    'Last Update': updated,
                                                    'Description': desc,
                                                    'CVSS': cvss,
                                                    'Vector': vector,
                                                    'URL': settings.APIURL['opencve']['url'].replace('/api','')+'/cve/%s' % (id,)
                                                })
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
                        with session.get(url) as response:
                            if response.status_code == 200:
                                cvedetails = response.json()
                                id = cvedetails['id']
                                creation = cvedetails['created_at']
                                updated = cvedetails['updated_at']
                                desc = regex.sub('',cvedetails['summary'])
                                if 'v3' in cvedetails['cvss']:
                                    cvss = cvedetails['cvss']['v3']
                                    if 'cvssMetricV31' in cvedetails['raw_nvd_data']['metrics']:
                                        vector = cvedetails['raw_nvd_data']['metrics']['cvssMetricV31'][0]['cvssData']['vectorString']
                                    elif 'cvssMetricV30' in cvedetails['raw_nvd_data']['metrics']:
                                        vector = cvedetails['raw_nvd_data']['metrics']['cvssMetricV30'][0]['cvssData']['vectorString']
                                elif 'v2' in cvedetails['cvss']:
                                    cvss = cvedetails['cvss']['v2']
                                    vector = cvedetails['raw_nvd_data']['metrics']['cvssMetricV2'][0]['cvssData']['vectorString']
                                else:
                                    cvss = 0.0
                                cves.append({
                                    'CVE ID': id,
                                    'Created At': creation,
                                    'Last Update': updated,
                                    'Description': desc,
                                    'CVSS': cvss,
                                    'Vector': vector,
                                    'URL': settings.APIURL['opencve']['url'].replace('/api','')+'/cve/%s' % (id,)
                                })
                            else:
                                messages.append({'text': 'The specified CVE `%s` could not be found.' % (cve,)})
                    if len(cves):
                        cves = sorted(cves, key=lambda v: v['Last Update'], reverse=True)
                        count = 0
                        fields = ('CVE ID', 'Description', 'CVSS', 'Vector', 'Created At', 'Last Update')
                        if len(cves)>10:
                            text = '**OpenCVE results for `%s %s`: %d found, displaying newest 10**\n' % (querytype,' '.join(params),len(cves))
                        else:
                            text = '**OpenCVE results for `%s %s`: %d found**\n' % (querytype,' '.join(params),len(cves))
                        text += '\n'
                        for field in fields:
                            text += '| %s ' % (field,)
                        text += '|\n'
                        for field in fields:
                            if field in ('CVE ID', 'CVSS', 'Created At', 'Last Update'):
                                text += '| -: '
                            else:
                                text += '| :- '
                        text += '|\n'
                        while count < 10 and count < len(cves):
                            cve = cves[count]
                            for field in fields:
                                if field in ('CVE ID'):
                                    text += '| [%s](%s) ' % (cve[field],cve['URL'])
                                else:
                                    text += '| %s ' % (cve[field],)
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
