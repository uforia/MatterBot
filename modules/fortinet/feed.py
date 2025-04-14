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
import feedparser
import os
import re
import requests
import sys
import traceback
import time

from pathlib import Path

try:
    from modules.fortinet import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/fortinet/settings.py').is_file():
        try:
            from modules.fortinet import settings
        except ModuleNotFoundError: # local test run
            import settings

def importScore():
    # Import dynamic threshold score from opencve module
    running = os.path.abspath(__file__)
    cwd = os.path.abspath(os.path.join(os.path.dirname(running), '..'))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    from opencve.defaults import ADVISORYTHRESHOLD
    return ADVISORYTHRESHOLD

def checkPage(link):
    try: # Check if feed url contains CVSS property on page
        with requests.Session() as session:
            response = session.get(link, headers={'User-Agent': 'MatterBot RSS Automation 1.0'})
            response.raise_for_status()
            data = bs4.BeautifulSoup(response.content, "html.parser")
            matches = data.select('td a[href^=" https://nvd.nist.gov/"]')
    except requests.exceptions.RequestException as e:
        matches = False
        print({f"An HTTP error occurred querying Fortinet PSIRT Advisories:\nError: {str(e)}\n{traceback.format_exc()}"}) 
        time.sleep(5)
    return matches

def query(MAX=settings.ENTRIES):
    items = []
    for URL in settings.URLS:
        feed = feedparser.parse(str(URL), agent='MatterBot RSS Automation 1.0')
        count = 0
        stripchars = '`\\[\\]\'\"'
        regex = re.compile('[%s]' % stripchars)
        while count < MAX:
            try:
                title = feed.entries[count].title
                link = feed.entries[count].link               
                # Check if feed contains CVSS scores
                THRESHOLD = importScore()
                matches = checkPage(link)
                filtered = False
                if not matches:
                    filtered = True
                else:
                    for score in matches:
                        # Check if CVSS score meets threshold
                        if float(score.text.strip()) > THRESHOLD:
                            cvss = float(score.text.strip())
                            filtered = True
                if filtered:
                    content = settings.NAME + ': [' + title
                    try:
                        content += f' (CVSS {cvss})'
                    except NameError:
                        pass
                    content += ']' + '(' + link + ')'
                    if len(feed.entries[count].description):
                        description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text("\n")).strip().replace('\n','. ')
                        if len(description)>400:
                            description = description[:396]+' ...'
                        content += '\n>'+description+'\n'
                    for channel in settings.CHANNELS:
                        items.append([channel, content])
                count+=1
            except IndexError:
                return items # No more items
    return items

if __name__ == "__main__":
    print(query())
