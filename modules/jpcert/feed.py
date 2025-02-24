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

import asyncio
import bs4
import feedparser
import googletrans
import re
from pathlib import Path
try:
    from modules.jpcert import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/jpcert/settings.py').is_file():
        try:
            from modules.jpcert import settings
        except ModuleNotFoundError: # local test run
            import settings

async def translateTitle(title):
    translator = googletrans.Translator()
    res = await translator.translate(title)
    return str(res)

def query(MAX=settings.ENTRIES):
    items = []
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
    count = 0
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    while count < MAX:
        try:
            title = feed.entries[count].title
            if settings.TRANSLATION:
                translatedTitle = asyncio.run(translateTitle(title))
                pattern = r'text=(.*?), pronunciation'
                match = re.search(pattern, str(translatedTitle))
                if match:
                    title = match.group(1)
            link = feed.entries[count].link
            content = settings.NAME + ': [' + title + '](' + link + ')'
            for channel in settings.CHANNELS:
                items.append([channel, content])
            count+=1
        except IndexError:
            return items # No more items
    return items



if __name__ == "__main__":
    print(query())
