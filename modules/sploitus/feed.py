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
import requests
import sys

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
            matches = data.select('div.tile-subtitle.text-gray') # Check if feed url contains CVSS property on page 
    except requests.exceptions.RequestException:
        matches = False
    return matches

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
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
    count = 0
    while count < settings.ENTRIES:
        try:
            content = None
            title = feed.entries[count].title[:-8] # Remove standard 'exploit' str from title
            link = feed.entries[count].link
            if settings.FILTER:
                THRESHOLD = importScore()
                matches = checkPage(link)
                filtered = False
                if not matches:
                    cvss = False
                    filtered = True
                else:
                    cvss = ''.join([score.text.strip()[-3:] for score in matches])
                    for score in matches:
                        if float(score.text.strip()[-3:]) >= THRESHOLD: # Check if CVSS score meets threshold
                            filtered = True
                if filtered:
                    content = settings.NAME + ': [' + title
                    if cvss:
                        content += f' - CVSS: `{cvss}`'
                    content += '](' + link + ')'
            else:
                content = settings.NAME + ': [' + title + '](' + link + ')'
            # TODO: query opencve api and get description?
            if content:
                for channel in settings.CHANNELS:
                    items.append([channel, content])
            count += 1
        except IndexError:
            return items # No more items
    return items

if __name__ == "__main__":
    print(query())
