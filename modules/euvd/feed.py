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

import bs4
import re
import requests
import traceback
from pathlib import Path
try:
    from modules.euvd import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/euvd/settings.py').is_file():
        try:
            from modules.euvd import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'MatterBot Feed Automation 1.0',
    }
    try:
        for category in settings.CATEGORIES:
            feedurl = settings.CATEGORIES[category]
            with requests.get(feedurl, headers=headers) as response:
                if response.status_code in (200,204):
                    json_response = response.json()
                    for vulnerability in json_response:
                        id = vulnerability['id']
                        description = vulnerability['description']
                        if len(description):
                            description = regex.sub('',bs4.BeautifulSoup(description,'lxml').get_text("\n")).strip().replace('\n','. ')
                            if len(description)>400:
                                description = description[:396]+' ...'
                        cat = category.split('/')[-1].replace('-',' ').title()
                        cvss = vulnerability['baseScore']
                        link = settings.BASEDETAILURL+id
                        content = f"{settings.NAME} - {cat}: [{id}]({link}) - CVSS: {cvss}"
                        content += '\n>'+description+'\n'
                        for channel in settings.CHANNELS:
                            items.append([channel, content])
                else:
                    content = f"An error occurred pulling the EUVD {category} feed: {response.content} ({response.status_code})"
                    items.append([channel, content])
    except Exception as e:
        content = "A Python error occurred in the EUVD module: `%s`\n```%s```\n" % (str(e), traceback.format_exc())
        items.append([channel, content])
    finally:
        return items

if __name__ == "__main__":
    print(query())
