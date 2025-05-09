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
from pathlib import Path
try:
    from modules._0day import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/_0day/settings.py').is_file():
        try:
            from modules._0day import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
    count = 0
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    pattern = r'(.*?)(#\w+)' # Filter hashtags
    while count < MAX:
        try:
            title = re.findall(pattern, regex.sub('',feed.entries[count].title))[2][0].strip()
            link = feed.entries[count].link
            content = settings.NAME + ': [' + title + '](' + link + ')'
            if 'title_detail' in feed.entries[count]:
                if 'value' in feed.entries[count]['title_detail']:
                    description = re.findall(pattern, regex.sub('',bs4.BeautifulSoup(feed.entries[count]['title_detail']['value'],'lxml').get_text("\n")).strip().replace('\n','. '))[2][0].strip()
                    if len(description) > 400:
                        description = description[:396] + ' ...'
                    content += '\n>'+ description +'\n'
            for channel in settings.CHANNELS:
                items.append([channel, content])
            count += 1
        except IndexError:
            return items # No more items
    return items

if __name__ == "__main__":
    print(query())
