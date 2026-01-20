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

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here

def importScore():
    running = os.path.abspath(__file__)
    cwd = os.path.abspath(os.path.join(os.path.dirname(running), '..'))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    from opencve.defaults import ADVISORYTHRESHOLD # Import threshold score from opencve module
    return ADVISORYTHRESHOLD

def checkPage(link):
    try:
        with requests.Session() as session: 
            response = session.get(link, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                })
                # 'User-Agent': 'MatterBot RSS Automation 1.0'
            response.raise_for_status()
            data = bs4.BeautifulSoup(response.content, "html.parser")
            matches = data.select('span.veeam-tooltip') # Check if feed url contains CVSS property on page 
    except requests.exceptions.RequestException:
        matches = False
    return matches

def query(MAX=settings.ENTRIES):
    items = []
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
    count = 0
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    while count < MAX:
        try:
            title = feed.entries[count].title
            link = feed.entries[count].link
            content = None # Make sure iteration can continue if no match is present
            if settings.FILTER:
                THRESHOLD = importScore()
                matches = checkPage(link)
                filtered = False
                if matches:
                    for score in matches:
                        try:
                            cvss = float(score.get_text(strip=True)[:3])
                            if cvss >= THRESHOLD: # Check if CVSS score meets threshold
                                filtered = True
                        except ValueError:
                            count+=1
                if filtered:
                    content = settings.NAME + ': [Critical ' + title + '](' + link + ')'
            else: # Filter is off
                content = settings.NAME + ': [' + title + '](' + link + ')'
            if content:
                for channel in settings.CHANNELS:
                    items.append([channel, content])
            count+=1
        except IndexError:
            return items # No more items
    return items

if __name__ == "__main__":
    print(query())
