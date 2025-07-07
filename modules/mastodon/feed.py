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
import re
import requests
from pathlib import Path
try:
    from modules.tripwire import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/tripwire/settings.py').is_file():
        try:
            from modules.tripwire import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    user_agent = 'MatterBot RSS Automation 1.0'
    headers = {
        'Content-Type': 'text/json',
        'User-Agent': f"{user_agent}",
    }
    for url in settings.URLS:
        title = url
        feed = feedparser.parse(settings.URLS[url], agent=user_agent)
        count = 0
        stripchars = '`\\[\\]\'\"'
        regex = re.compile('[%s]' % stripchars)
        while count < MAX:
            try:
                link = feed.entries[count].link
                content = settings.NAME + ': [' + title + '](' + link + ')'
                if len(feed.entries[count].description):
                    description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text("\n")).strip().replace('\n','. ')
                    if len(description)>400:
                        description = description[:396]+' ...'
                    content += '\n>'+description+'\n'
                upload = None
                if 'media_content' in feed.entries[count]:
                    for media in feed.entries[count]['media_content']:
                        if 'url' in media:
                            url = media['url']
                            with requests.get(url, headers=headers) as response:
                                if response.status_code in (200,206):
                                    filename = url.split('/')[-1]
                                    bytes = response.content[:50]
                                    upload = {'filename': filename, 'bytes': bytes}
                for channel in settings.CHANNELS:
                    if upload:
                        items.append([channel, content, {'uploads': [upload]}])
                    else:
                        items.append([channel, content])
                count+=1
            except IndexError:
                return items # No more items
    return items

if __name__ == "__main__":
    print(query())
