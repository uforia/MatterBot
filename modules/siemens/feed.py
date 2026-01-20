#!/usr/bin/env python3

# Every module must set the CHANNELS variable to indicate where information should be sent to in Mattermost
#
# Every module must implement the query() function.
# This query() function is called by the main worker and has only one parameter: the number of historic
# items that should be returned in the list.
#
# Every module must return a list [...] with 0, 1 ... n entries
# of 2-tuples: ('<channel>', '<content>')
#
# <channel>: basically the destination channel in Mattermost, e.g. 'Newsfeed', 'Incident', etc.
# <content>: the content of the message, MD format possible

import os
import sys
import requests
import traceback

def importScore():
    running = os.path.abspath(__file__)
    cwd = os.path.abspath(os.path.join(os.path.dirname(running), '..'))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    from opencve.defaults import ADVISORYTHRESHOLD # Import threshold score from opencve module
    return ADVISORYTHRESHOLD

def query(settings=None):
    if settings:
        try:
            from types import SimpleNamespace
            settings = SimpleNamespace(**settings)
        except:
            pass
    else:
        import defaults as settings
        try:
            import settings as _override
            settings.__dict__.update({k: v for k, v in vars(_override).items() if not k.startswith('__')})
        except ImportError:
            pass
    items = []
    stripchars = '`\\[\\]\'\"'
    count = 0
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'MatterBot Feed Automation 1.0',
    }
    while count < settings.ENTRIES:
        try:
            with requests.get(settings.URL, headers=headers) as response: # Request advisories
                if response.status_code in (200,204):
                    jsonFeed = response.json()
                    detailURL = None
                    for link in jsonFeed['feed']['entry'][count]['link']: # Get detailed mapping for url and cvss
                        if link.get('rel') == 'self':
                            detailURL = link['href']
                            break
                    if not detailURL:
                        raise ValueError("No link found")
                    with requests.get(detailURL, headers=headers) as response:
                        if response.status_code in (200,204):
                            jsonAdvisory = response.json()
                            link = next((
                                ref.get('url')
                                for ref in jsonAdvisory.get('document', {}).get('references', [])
                                if ref.get('category') == 'self'
                                ),
                                None
                            )
                            for vulnerability in jsonAdvisory.get('vulnerabilities', []): # Parse values
                                cve = vulnerability.get('cve')
                                cvss = (
                                    vulnerability.get('scores', [{}])[0]
                                    .get('cvss_v3', {})
                                    .get('baseScore')
                                )
                                summary = (
                                    vulnerability.get('notes', [{}])[0]
                                    .get('text')
                                )
                                if len(summary)>400:
                                    summary = summary[:396]+' ...'
                                if settings.FILTER: # Check if CVSS score meets threshold
                                    THRESHOLD = importScore()
                                    score = float(str(cvss).strip()) if cvss is not None else None
                                    if score is None or score < THRESHOLD:
                                        continue
                                    content = f"{settings.NAME}: [{cve}]({link}) - CVSS: `{cvss}`"
                                else:
                                    content = f"{settings.NAME}: [{cve}]({link}) - CVSS: `{cvss}`"
                                content += f"\n> {summary}\n"
            for channel in settings.CHANNELS:
                items.append([channel, content])
            count += 1
        except IndexError:
            return items
        except Exception as e:
            content = "A Python error occurred in the Siemens module: `%s`\n```%s```\n" % (str(e), traceback.format_exc())
            return items
    return items

if __name__ == "__main__":
    print(query())
