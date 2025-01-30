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
    items = set()
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
        filtered = False
        productlist = set()
        while count < MAX:
            try:
                entry = json_response['results'][count]
                cve = entry['cve_id']
                title = unicodedata.normalize('NFKD',entry['description'])
                for product in settings.PRODUCTFILTER:
                    pfregex = re.compile('%s' % product)
                    matches = pfregex.search(title)
                    if matches:
                        filtered = True
                if not filtered:
                    last_update = entry['updated_at']
                    historyitem = (cve,last_update)
                    if not historyitem in history['opencve']:
                        if settings.PUBLICDESCURL:
                            link = f"https://app.opencve.io/cve/{cve}"
                        else:
                            link = f"{settings.URL}/cve/{cve}"
                        description = regex.sub('',title).strip().replace('\n','. ')
                        if len(description)>400:
                            description = description[:396]+' ...'
                        cve_details_response = session.get(settings.URL+settings.API+f'/cve/{cve}')
                        if cve_details_response.status_code == 200:
                            cvss = 0.0
                            vector = 'N/A'
                            cve_details = cve_details_response.json()
                            for cvssversion in ('cvssV4_0', 'cvssV3_1', 'cvssV3_0', 'cvssV2_0'):
                                if cvssversion in cve_details['metrics']:
                                    cvssdata = cve_details['metrics'][cvssversion]
                                    if len(cvssdata['data']):
                                        cvss = cvssdata['data']['score']
                                        vector = cvssdata['data']['vector']
                                        break
                            content = settings.NAME + f': [{cve}]({link}) - CVSS: `{cvss}`\n>{description}\n'
                            if (isinstance(cvss,float) and cvss >= settings.THRESHOLD) or settings.NOCVSS:
                                for channel in settings.CHANNELS:
                                    items.add((channel, content))
                                    history['opencve'].append(historyitem)
                            if settings.AUTOADVISORY:
                                if isinstance(cvss,float):
                                    if cvss > settings.ADVISORYTHRESHOLD:
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
                                                        msg = f'**A vulnerability has been published which CVSS score exceeds the threshold:**\n{content}\n*A manual asset management check may be required for this CVE.*'
                                                    else:
                                                        msg = f'**A vulnerability has been published which CVSS score exceeds the threshold:**\n{content}\n*An automatic asset management check is triggered for this CVE:*\n\n' + ' '.join([lookup,productname])
                                                    items.add((channel, msg))
                count+=1
            except IndexError:
                return items # No more items
            except Exception as e:
                print(traceback.format_exc())
        return items

if __name__ == "__main__":
    for item in query():
        print(item)
