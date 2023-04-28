#!/usr/bin/env python3

import datetime
import json
import os
import pypandoc
import requests
from pathlib import Path
try:
    from commands.ewa import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/ewa/settings.py').is_file():
        try:
            from commands.ewa import settings
        except ModuleNotFoundError: # local test run
            import settings


def process(command, channel, username, params):
    messages = []
    try:
        if len(params)>1:
            command = params[0].lower()
            cve = params[1].upper()
            if not command in ('create', 'pdf'):
                messages.append({'text': "Please choose to `create` a WikiJS page for a CVE, or to generate a `pdf` for a CVE!"})
            elif not cve.startswith('CVE-'):
                messages.append({'text': "Please specify the CVE number, e.g.: `CVE-2023-20855`!"})
            else:
                cvssMetrics = ['cvssMetricV31', 'cvssMetric30', 'cvssMetric21']
                headers = {
                    'Authorization': 'Bearer %s' % settings.APIURL['ewa']['token'],
                    'Content-Type': settings.CONTENTTYPE,
                }
                if command == 'pdf':
                    ### Create a PDF from the page
                    contentid = None
                    query = """
                        {
                            pages {
                                list (orderBy: TITLE) {
                                    id,
                                    title
                                }
                            }
                        }
                    """
                    query = json.dumps({'query': query.strip()})
                    with requests.post(settings.APIURL['ewa']['url']+'/graphql', headers=headers, data=query) as response:
                        json_response = response.json()
                        if 'data' in json_response:
                            if 'pages' in json_response['data']:
                                if 'list' in json_response['data']['pages']:
                                    for result in json_response['data']['pages']['list']:
                                        if result['title'] == cve:
                                            contentid = result['id']
                    if contentid:
                        query = """
                            {
                                pages {
                                    single ( id: """+str(contentid)+""" ) {
                                        content
                                    }
                                }
                            }
                        """
                        query = json.dumps({'query': query.strip()})
                        try:
                            with requests.post(settings.APIURL['ewa']['url']+'/graphql', headers=headers, data=query) as response:
                                json_response = response.json()
                                content = json_response['data']['pages']['single']['content']
                                doc = pypandoc.convert_text(content, 'html', format='markdown')
                                pwd = os.getcwd()
                                os.chdir(settings.HTMLTEMPLATEDIR)
                                with open(settings.HTMLHEADER) as f:
                                    htmlheader = f.read()
                                with open(settings.HTMLCSS) as f:
                                    css = "<style>\n" + f.read() + "\n</style>\n<body>\n"
                                with open(settings.HTMLFOOTER) as f:
                                    htmlfooter = f.read()
                                html = htmlheader + css + doc + htmlfooter
                                with open('../'+cve+'.html', 'wb') as f:
                                    f.write(html.encode())
                                    f.flush()
                                output = pypandoc.convert_file('../'+cve+'.html', 'pdf', outputfile='../'+cve+'.pdf')
                                assert output == ""
                                try:
                                    os.unlink('../'+cve+'.html')
                                    with open('../'+cve+'.pdf', 'rb') as f:
                                        bytes = f.read()
                                    if len(bytes):
                                        messages.append({
                                            'text': 'Early Warning / Advisory PDF for '+cve,
                                            'uploads': [
                                                {'filename': cve+'.pdf', 'bytes': bytes}
                                            ]
                                        })
                                    os.unlink('../'+cve+'.pdf')
                                except:
                                    raise
                        except:
                            raise
                        finally:
                            os.chdir(pwd)
                    else:
                        messages.append({'text': "**EAW Error**: there is no CVE page yet for `%s`" % (cve,)})
                if command == 'create':
                    ### Download the CVE information
                    content = None
                    with requests.get(settings.APIURL['nvd']['url']+cve) as response:
                        json_response = response.json()
                        if 'resultsPerPage' in json_response:
                            if json_response['resultsPerPage'] == 1:
                                vulnerability = json_response['vulnerabilities'][0]['cve']
                                cveid = vulnerability['id']
                                title = vulnerability['descriptions'][0]['value']
                                cvssMetrics = vulnerability['metrics']
                                for metrictype in cvssMetrics:
                                    if metrictype in cvssMetrics:
                                        cvssMetric = cvssMetrics[metrictype][0]
                                        vectorString = cvssMetric['cvssData']['vectorString']
                                        baseScore = cvssMetric['cvssData']['baseScore']
                                        baseSeverity = cvssMetric['cvssData']['baseSeverity']
                                        exploitability = cvssMetric['exploitabilityScore'] if 'exploitabilityScore' in cvssMetric else None
                                        impactScore = cvssMetric['impactScore'] if 'impactScore' in cvssMetric else None
                                        break
                                referenceUrls = set()
                                references = vulnerability['references']
                                for reference in references:
                                    referenceUrls.add(reference['url'])
                                productnames = set()
                                if 'configurations' in vulnerability:
                                    configurations = vulnerability['configurations']
                                    for configuration in configurations:
                                        if 'nodes' in configuration:
                                            nodes = configuration['nodes']
                                            for node in nodes:
                                                for cpeMatch in node['cpeMatch']:
                                                    productnames.add(cpeMatch['criteria'].split(':')[4].replace('_',' ').title())
                                content = "\n# **%s**" % (settings.EWAHEADER,)
                                content += "\n\n"
                                content += "## **%s**: %s" % (settings.VULNTEXT, cveid)
                                content += "\n\n"
                                content += "\n|  |  |"
                                content += "\n|:-|:-|"
                                content += "\n| **%s** | %s |" % (settings.DESCTEXT, title)
                                content += "\n| **%s** | %s |" % (settings.DATETEXT, datetime.datetime.now().strftime('%A, %d %B %Y'))
                                content += "\n| **%s** | 1.0 |" % (settings.REVTEXT,)
                                content += "\n| **CVSS Score** | %s (%s) |" % (baseScore, baseSeverity)
                                if exploitability:
                                    if exploitability<=3.9:
                                        chance = settings.LOWTEXT
                                    elif exploitability>=4.0 and exploitability<=6.9:
                                        chance = settings.MEDTEXT
                                    elif exploitability>=7.0:
                                        chance = settings.HIGHTEXT
                                    content += "\n| **%s** | %s |" % (settings.CHANCETEXT, chance)
                                if impactScore:
                                    if impactScore<=3.9:
                                        schade = settings.LOWTEXT
                                    elif impactScore>=4.0 and impactScore<=6.9:
                                        schade = settings.MEDTEXT
                                    elif impactScore>=7.0:
                                        schade = settings.HIGHTEXT
                                    content += "\n| **%s** | %s |" % (settings.DMGTEXT, schade)
                                content += "\n| **CVSS String** | %s |" % (vectorString,)
                                if len(productnames):
                                    content += "\n| **%s** | %s |" % (settings.PRODTEXT, ', '.join(productnames))
                                if len(referenceUrls):
                                    content += "\n| **%s** | [%s](%s) |" % (settings.REFTEXT, ', '.join(referenceUrls), ', '.join(referenceUrls))
                                content += "\n| **%s** | ... |" % (settings.ADDDESCTEXT)
                                content += "\n| **%s** | ... |" % (settings.SOLTEXT)
                                content += "\n\n"
                                content += "<div style=\"page-break-after: always;\"></div>"
                                content += "## %s" % (settings.FAQTEXT)
                                content += "\n\n"
                                content += settings.FAQCONTENT
                                content += "\n\n"
                                content += "## %s" % (settings.DISCTEXT)
                                content += "\n\n"
                                content += settings.DISCCONTENT
                                content += "\n\n"
                            if content:
                                ### Create a WikiJS page
                                description = "%s" % (title,)
                                editor = "markdown"
                                isPublished = "true"
                                isPrivate = "false"
                                locale = "en"
                                path = "/home/%s" % (cveid,)
                                tags = "[" + settings.TAGS + ", "
                                tags += "\"%s\"]" % (cveid,)
                                title = "%s" % (cveid,)
                                query = """
                                mutation Page {
                                    pages {
                                        create (
                                            content: \"\"\"%s\"\"\",
                                            description: \"\"\"%s\"\"\",
                                            editor: "%s",
                                            isPublished: %s,
                                            isPrivate: %s,
                                            locale: "%s",
                                            path: "%s",
                                            tags: %s,
                                            title: \"\"\"%s\"\"\"
                                        )
                                        {
                                            responseResult {
                                                succeeded,
                                                errorCode,
                                                slug,
                                                message
                                            },
                                            page {
                                                id,
                                                path,
                                                title
                                            }
                                        }
                                    }
                                }
                                """ % (content, description, editor, isPublished, isPrivate, locale, path, tags, title,)
                                query = json.dumps({'query': query.strip()})
                                with requests.post(settings.APIURL['ewa']['url']+'/graphql', headers=headers, data=query) as response:
                                    json_response = response.json()
                                    if 'data' in json_response:
                                        if 'pages' in json_response['data']:
                                            if 'create' in json_response['data']['pages']:
                                                messages.append({'text': "Early Warning / Advisory page generated for ["+cve+"]("+settings.APIURL['ewa']['url']+"/"+locale+path+")"})
    except Exception as e:
        messages.append({'text': "An error occurred: %s" % (str(e),)})
    finally:
        return {'messages': messages}