#!/usr/bin/env python3

import datetime
import json
import os
import pypandoc
import requests
import weasyprint
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
                                MODULEDIR = "commands/ewa/"
                                mdfile = MODULEDIR+cve+'.md'
                                htmlfile = MODULEDIR+cve+'.html'
                                cssfile = MODULEDIR+settings.HTMLCSS
                                pdffile = MODULEDIR+cve+'.pdf'
                                format = 'markdown'
                                extra_args = ['--section-divs', '--number-offset=0']
                                with open(MODULEDIR+settings.HTMLHEADER) as f:
                                    header = f.read()
                                    header = header.replace('%title%', settings.EWAHEADER)
                                    header = header.replace('%subtitle%', cve)
                                    header = header.replace('%toc%', '[TOC]')
                                    header = header.replace('%date%', datetime.datetime.now().strftime('%A, %d %B %Y'))
                                with open(MODULEDIR+settings.HTMLFOOTER) as f:
                                    footer = f.read()
                                html = header + pypandoc.convert_text(content, 'html', format=format, extra_args=extra_args) + footer
                                html = html.replace('</div>','</div><div class="logo"><img src="template/img/kpn-logo-groen.png" /></div>')
                                with open(mdfile, 'wb') as f:
                                    f.write(content.encode())
                                    f.flush()
                                with open(htmlfile, 'wb') as f:
                                    f.write(html.encode())
                                    f.flush()
                                html_writer = weasyprint.HTML(htmlfile)
                                css = weasyprint.CSS(filename=MODULEDIR+settings.HTMLCSS, base_url=MODULEDIR+settings.HTMLTEMPLATEDIR)
                                html_writer.write_pdf(pdffile, stylesheets=[cssfile])
                                try:
                                    with open(pdffile, 'rb') as f:
                                        bytes = f.read()
                                    if len(bytes):
                                        messages.append({
                                            'text': 'Early Warning / Advisory PDF generated for '+cve,
                                            'uploads': [
                                                {'filename': cve+'.pdf', 'bytes': bytes}
                                            ]
                                        })
                                    #os.unlink(mdfile)
                                    #os.unlink(htmlfile)
                                    #os.unlink(pdffile)
                                except:
                                    raise
                        except:
                            raise
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
                                vectorString = None
                                baseScore = None
                                baseSeverity = None
                                exploitability = None
                                impactScore = None
                                for metrictype in cvssMetrics:
                                    if metrictype in cvssMetrics:
                                        if 'cvssData' in cvssMetrics:
                                            cvssMetric = cvssMetrics[metrictype][0]
                                            cvssData = cvssMetric['cvssData']
                                            vectorString = cvssData['vectorString']
                                            baseScore = cvssData['baseScore']
                                            baseSeverity = cvssData['baseSeverity']
                                            exploitability = cvssMetric['exploitabilityScore']
                                            impactScore = cvssMetric['impactScore']
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
                                content += "\n|:-|:----|"
                                content += "\n| **%s** | %s |" % (settings.DESCTEXT, title)
                                content += "\n| **%s** | %s |" % (settings.DATETEXT, datetime.datetime.now().strftime('%A, %d %B %Y'))
                                content += "\n| **%s** | 1.0 |" % (settings.REVTEXT,)
                                if baseScore and baseSeverity:
                                    content += "\n| **CVSS Score** | %s (%s) |" % (baseScore, baseSeverity)
                                else:
                                    content += "\n| **CVSS Score** | Unknown (N/A) |"
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
                                    content += "\n| **%s** | " % (settings.REFTEXT)
                                    for referenceUrl in referenceUrls:
                                        content += "[%s](%s), " % (referenceUrl, referenceUrl)
                                    content = content[:-2]
                                    content += " |"
                                content += "\n\n"
                                content += "\n<div style=\"page-break-after: always;\"></div>"
                                content += "\n\n"
                                content += "\n## **%s**" % (settings.ADDDESCTEXT)
                                content += "\n\n"
                                content += "..."
                                content += "\n\n"
                                content += "\n## **%s**" % (settings.SOLTEXT)
                                content += "\n\n"
                                content += "..."
                                content += "\n\n"
                                content += "\n<div style=\"page-break-after: always;\"></div>"
                                content += "\n\n"
                                content += "\n# %s" % (settings.FAQTEXT)
                                content += "\n"
                                content += settings.FAQCONTENT
                                content += "\n\n"
                                content += "# %s" % (settings.DISCTEXT)
                                content += "\n"
                                content += settings.DISCCONTENT
                                content += "\n"
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
                            elif json_response['resultsPerPage'] == 0:
                                messages.append({'text': "`%s` does not exist in the NVD." % (cve,)})
                        else:
                            messages.append({'text': "An error occurred querying the NVD!"})
    except Exception as e:
        messages.append({'text': "An error occurred: %s" % (str(e),)})
    finally:
        return {'messages': messages}
