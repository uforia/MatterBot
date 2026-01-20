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

### Dynamic configuration loader (do not change/edit)
import importlib
import sys
from pathlib import Path
_pkg_name = Path(__file__).parent.name
_module_dir = Path(__file__).parent
if str(_module_dir) not in sys.path:
    sys.path.insert(0, str(_module_dir))
try:
    defaults_mod = importlib.import_module(f'commands.{_pkg_name}.defaults')
except ModuleNotFoundError:
    try:
        defaults_mod = importlib.import_module('defaults')
    except ModuleNotFoundError:
        print(f"Module {_pkg_name} could not be loaded due to a missing default configuration.")
try:
    settings_mod = importlib.import_module(f'commands.{_pkg_name}.settings')
except ModuleNotFoundError:
    try:
        settings_mod = importlib.import_module('settings')
    except ModuleNotFoundError:
        settings_mod = None
settings = {k: v for k, v in vars(defaults_mod).items() if not k.startswith('__')}
if settings_mod:
    settings.update({k: v for k, v in vars(settings_mod).items() if not k.startswith('__')})
from types import SimpleNamespace
settings = SimpleNamespace(**settings)
### Loader end, actual module functionality starts here

def importScore():
    running = os.path.abspath(__file__)
    cwd = os.path.abspath(os.path.join(os.path.dirname(running), '..'))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    from opencve.defaults import ADVISORYTHRESHOLD # Import threshold score from opencve module
    return ADVISORYTHRESHOLD

def checkPage(link):
    try: # Check if feed url contains CVSS property on page
        with requests.Session() as session:
            response = session.get(link, headers={'User-Agent': 'MatterBot RSS Automation 1.0'})
            response.raise_for_status()
            data = bs4.BeautifulSoup(response.content, "html.parser")
            selection = [ # Check if feed url contains CVSS property on page, based on feeds
                'table.outbreak-alert-table tr',
                'td a[href^=" https://nvd.nist.gov/"]'
            ]
            for page in selection:
                matches = data.select(page)
                if page[0]: # Get seperate value from table using filter
                    for row in matches:
                        columns = row.find_all("td")
                        if len(columns) >= 3 and "CVSS Rating" in columns[1].text:
                            tableScore = columns[2].text.strip()
    except requests.exceptions.RequestException:
        matches = False
    try: # Return dynamic values
        return matches, tableScore
    except NameError:
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
                if settings.FILTER:
                    THRESHOLD = importScore()
                    matches = checkPage(link)
                    filtered = False
                    if not matches:
                        cvss = False
                        filtered = True
                    else:
                        if isinstance(matches, tuple): # Filter for return values from checkPage()
                            cvss = matches[1]
                            if float(cvss) >= THRESHOLD:
                                filtered = True
                        else:
                            for score in matches:
                                if float(score.text.strip()) >= THRESHOLD: # Check if CVSS score meets threshold
                                    cvss = float(score.text.strip())
                                    filtered = True
                    if filtered:
                        content = settings.NAME + ': [' + title
                        if cvss:
                            content += f' - CVSS: `{cvss}`'
                        content += '](' + link + ')'
                else:
                    content = settings.NAME + ': [' + title + '](' + link + ')'
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
