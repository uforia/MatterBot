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

import re
import requests
import shelve
import sys
import traceback
import unicodedata
from pathlib import Path
try:
    from modules.opencve import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/opencve/settings.py').is_file():
        try:
            from modules.opencve import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    count = 0
    stripchars = r'`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    try:
        if Path(settings.HISTORY).is_file():
            history = shelve.open(settings.HISTORY,writeback=True)
        else:
            if Path('modules/opencve/'+settings.HISTORY).is_file():
                history = shelve.open('modules/opencve/'+settings.HISTORY,writeback=True)
        if not Path(settings.HISTORY).is_file() and not Path('modules/opencve/'+settings.HISTORY).is_file():
            if Path('feed.py').is_file():
                history = shelve.open(settings.HISTORY,writeback=True)
            else:
                if Path('modules/opencve/feed.py').is_file():
                    history = shelve.open('modules/opencve/'+settings.HISTORY,writeback=True)
        if not 'opencve' in history:
            history['opencve'] = []
    except Exception as e:
        print(traceback.format_exc())
        raise
    if history:
        session = requests.Session()
        session.auth = (settings.USERNAME,settings.PASSWORD)
        with session.get(settings.URL+settings.API+'/cve') as response:
            if response.status_code == 200:
                json_response = response.json()
    if json_response:
        cwe_cache = {}
        while count < MAX:
            try:
                cve = json_response[count]['id']
                title = unicodedata.normalize('NFKD',json_response[count]['summary'])
                last_update = json_response[count]['updated_at']
                historyitem = (cve,last_update)
                if not historyitem in history['opencve']:
                    link = settings.URL+'/cve/'+cve
                    description = regex.sub('',title).strip().replace('\n','. ')
                    if len(description)>400:
                        description = description[:396]+' ...'
                    cve_details_response = session.get(settings.URL+settings.API+f'/cve/{cve}')
                    if cve_details_response.status_code == 200:
                        cve_details = cve_details_response.json()
                    if 'cvss' in cve_details:
                        if 'v3' in cve_details['cvss']:
                            cvss = cve_details['cvss']['v3']
                        elif 'v2' in cve_details['cvss']:
                            cvss = cve_details['cvss']['v2']
                        else:
                            cvss = 'N/A'
                    if 'cwes' in cve_details:
                        cwes = ''
                        cwelist = cve_details['cwes']
                        for cwe in cwelist:
                            if not cwe in cwe_cache:
                                cwe_cache[cwe] = ''
                                cwe_details_response = session.get(settings.URL+settings.API+f'/cwe/{cwe}')
                                if cwe_details_response.status_code == 200:
                                    cwe_details = cwe_details_response.json()
                                    cwe_cache[cwe] = cwe_details['name']
                            cwes += f'[{cwe_cache[cwe]}]({settings.URL}{settings.API}/cwe/{cwe}), '
                        cwes = cwes[:-2]
                    if not len(cwes):
                        cwes = '`N/A`'
                    content = settings.NAME + f': [{cve}]({link}) - CVSS: `{cvss}` - CWEs: {cwes}\n>{description}\n'
                    if (settings.NOCVSS and cvss == 'N/A') or not settings.NOCVSS:
                        for channel in settings.CHANNELS:
                            items.append([channel,content])
                            history['opencve'].append(historyitem)
                    if settings.AUTOADVISORY:
                        if isinstance(cvss,float):
                            if cvss > settings.THRESHOLD:
                                productlist = set()
                                if 'vendors' in cve_details:
                                    vendors = cve_details['vendors']
                                    if len(vendors):
                                        for vendor in vendors:
                                            productlist.add(vendor)
                                    else:
                                        productlist.add(f'N/A {title}')
                                for productname in productlist:
                                    for channel in settings.ADVISORYCHANS:
                                        for lookup in settings.ADVISORYCHANS[channel]:
                                            if productname.startswith('N/A '):
                                                items.append([channel, f'**Manual Asset Management Lookup Needed**: [{cve}]({link}) - CVSS: `{cvss}` - CWEs: {cwes}:\n>{productname[4:]}\n'])
                                            else:
                                                items.append([channel, ' '.join([lookup,productname])])
                count+=1
            except IndexError:
                return items # No more items
            except Exception as e:
                print(traceback.format_exc())
        return items

if __name__ == "__main__":
    for item in query():
        print(item)
