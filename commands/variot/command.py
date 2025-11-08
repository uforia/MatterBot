#!/usr/bin/env python3

from bs4 import BeautifulSoup
import collections
import datetime
import re
import requests
import sys
import traceback
from pathlib import Path
try:
    from commands.variot import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/variot/settings.py').is_file():
        try:
            from commands.variot import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    stripchars = r'`\[\]\n\r\'\"|'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    headers = {
        'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for VARIoT v1.0',
    }
    if settings.APIURL['variot']['key']:
        headers['Authorization'] = settings.APIURL['variot']['key']
    try:
        query = None
        if len(params):
            if params[0].lower() == 'exploit' or params[0].upper().startswith('VAR-E-'):
                querytype = 'exploit'
                if len(params)>1:
                    query = params[1]
                else:
                    messages.append({'text': 'You must specify a VARIoT Exploit ID!'})
            elif params[0].lower() == 'vuln' or params[0].upper().startswith('VAR-'):
                querytype = 'vuln'
                if len(params)>1:
                    query = params[1]
                else:
                    messages.append({'text': 'You must specify a VARIoT Vulnerability ID!'})
            elif params[0].lower() == 'search':
                querytype = 'search'
                if len(params)>1:
                    query = params[1:]
                else:
                    messages.append({'text': 'You must specify something to search for!'})
            else:
                querytype = 'search'
                query = params[0:]
        if query:
            session = requests.Session()
            if querytype in 'exploit':
                url = settings.APIURL['variot']['url']+f"exploit/{query.upper()}/"
                with session.get(url=url, headers=headers) as response:
                    if response.status_code in (200,):
                        json_response = response.json()
                        exploitfields = collections.OrderedDict({
                            'Title': json_response['title']['data'],
                            'Description': regex.sub('',json_response['description']['data']),
                            'Tags': '` ,`'.join(sorted([_['tag'] for _ in json_response['tags']['data']])),
                            'MD5': json_response['exploit_hash']['data']['local']['md5'] if json_response['exploit_hash']['data']['local']['md5'] else '-',
                            'SHA1': json_response['exploit_hash']['data']['local']['sha-1'] if json_response['exploit_hash']['data']['local']['sha-1'] else '-',
                            'SHA256': json_response['exploit_hash']['data']['local']['sha-256'] if json_response['exploit_hash']['data']['local']['sha-256'] else '-',
                            'Release Date': datetime.datetime.strptime(json_response['sources_release_date']['data'][0]['date'], "%Y-%m-%dT%H:%M:%S").strftime("%B %d, %Y at %H:%M:%S UTC"),
                            'Last Updated': datetime.datetime.strptime(json_response['last_update_date'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%B %d, %Y at %H:%M:%S UTC"),
                        })
                        message = f"| VARIoT Results | `{query.upper()}` |\n"
                        message += "| :- | :- |\n"
                        for exploitfield in exploitfields:
                            message += f"| **{exploitfield}** | `{exploitfields[exploitfield]}` |\n"
                        if 'sources' in json_response:
                            sources = [(_['db'], _['url']) for _ in json_response['sources']['data']]
                            if len(sources):
                                message += "| **Sources** | "
                                for sourcetuple in sources:
                                    source, url = sourcetuple
                                    message += f"[{source}]({url}), "
                                message = message[:-2]
                                message += " |\n"
                        message += "\n\n"
                        exploitcode = json_response['exploit']['data']
                        messages.append({'text': message, 'uploads': [{'filename': f"{query}_exploit_code", 'bytes': exploitcode}]})
                    if response.status_code in (404,):
                        messages.append({'text': f"VARIoT exploit `{query}` not found!"})
            if querytype in 'vuln':
                url = settings.APIURL['variot']['url']+f"vuln/{query.upper()}/"
                with session.get(url=url, headers=headers) as response:
                    if response.status_code in (200,):
                        json_response = response.json()
                        try:
                            releasedate = datetime.datetime.strptime(json_response['sources_release_date']['data'][0]['date'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%B %d, %Y at %H:%M:%S UTC")
                        except:
                            releasedate = datetime.datetime.strptime(json_response['sources_release_date']['data'][0]['date'], "%Y-%m-%dT%H:%M:%S").strftime("%B %d, %Y at %H:%M:%S UTC")
                        try:
                            lastupdated = datetime.datetime.strptime(json_response['last_update_date'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%B %d, %Y at %H:%M:%S UTC")
                        except:
                            lastupdated = datetime.datetime.strptime(json_response['last_update_date'], "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y at %H:%M:%S UTC")
                        vulnfields = collections.OrderedDict({
                            'Description': regex.sub('',json_response['description']['data']),
                            'Release Date': releasedate,
                            'Last Updated': lastupdated,
                        })
                        message = f"| VARIoT Results | `{query.upper()}` |\n"
                        message += "| :- | :- |\n"
                        for vulnfield in vulnfields:
                            message += f"| **{vulnfield}** | `{vulnfields[vulnfield]}` |\n"
                        sources = [_['id'] for _ in json_response['sources']['data']]
                        if len(json_response['cvss']['data']):
                            baseScoreV2 = json_response['cvss']['data'][0]['cvssV2'][0]['baseScore'] if len(json_response['cvss']['data'][0]['cvssV2']) else None
                            severityV2 = json_response['cvss']['data'][0]['cvssV2'][0]['severity'] if len(json_response['cvss']['data'][0]['cvssV2']) else None
                            baseScoreV3 = json_response['cvss']['data'][0]['cvssV3'][0]['baseScore'] if len(json_response['cvss']['data'][0]['cvssV3']) else None
                            severityV3 = json_response['cvss']['data'][0]['cvssV3'][0]['baseSeverity'] if len(json_response['cvss']['data'][0]['cvssV3']) else None
                        if baseScoreV2:
                            message += f"| **CVSS v2** | `{baseScoreV2}` (`{severityV2}`) |\n"
                        if baseScoreV3:
                            message += f"| **CVSS v3** |  `{baseScoreV3}` (`{severityV3}`) |\n"
                        if 'references' in json_response:
                            references = [_['url'] for _ in json_response['references']['data']]
                            if len(references):
                                message += "| **References** | "
                                count = 1
                                for url in references:
                                    message += f"[Link #{count}]({url}), "
                                    count += 1
                                message = message[:-2]
                                message += " |\n"
                        message += "\n\n"
                        messages.append({'text': message})
                    if response.status_code in (404,):
                        messages.append({'text': f"VARIoT vulnerability `{query}` not found!"})
            if querytype in 'search':
                # Ugly hacks around here, since VARIoT does not support searching from the API
                url = settings.APIURL['variot']['url'].replace('/api','')+f"vulns/?free_text={'%20'.join(query)}"
                with session.get(url=url, headers=headers) as response:
                    if response.status_code in (200,):
                        parsed_html = BeautifulSoup(response.content, features='lxml')
                        items = parsed_html.body.find_all('div', attrs={'class':'accordion-item'})
                        if len(items):
                            vulnentries = parsed_html.body.find_all('div', attrs={'class':'accordion-item'})
                            count = 0
                            message = f"**VARIoT Search Results** for `{' '.join(query)}`\n\n"
                            message += "| **VAR ID** | **Title** | **CVE** | **CVSS** |\n"
                            message += "| -: | :- | -: | -: |\n"
                            while count < len(vulnentries):
                                vulnfields = vulnentries[count].find_all('td')
                                vulnfields = [_.text for _ in vulnfields]
                                var = ', '.join([_.strip() for _ in vulnfields[0].strip().split('\n')]).upper()
                                cve = ', '.join([_.strip() for _ in vulnfields[1].strip().split('\n')]).upper()
                                if len(cve)<9:
                                    cve = "N/A"
                                title = ' '.join(', '.join([_.strip() for _ in vulnfields[2].strip().split('\n')]).split())
                                cvss = ', '.join([_.strip() for _ in vulnfields[3].strip().split('\n')])
                                message += f"| [`{var}`](https://www.variotdbs.pl/vuln/{var}/) | `{title}` | `{cve}` | `{cvss}` |\n"
                                count += 1
                                if count>=10:
                                    message += "\n\n"
                                    message += f"*Found more than 10 entries, refine your search if needed!*"
                                    break
                            message += "\n\n"
                            messages.append({'text': message})
                        else:
                            messages.append({'text': 'No VARIoT results found for: `%s`' % (' '.join(query),)})
                    else:
                        messages.append({'text': 'An error occurred searching VARIoT:\nError: `%s`' % (response.status_code,)})
    except:
        messages.append({'text': 'An error occurred in the VARIoT module:\nError: `%s`' % (traceback.format_exc(),)})
    finally:
        return {'messages': messages}
