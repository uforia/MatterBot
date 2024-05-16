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
    from modules.ncscnl import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/ncscnl/settings.py').is_file():
        try:
            from modules.ncscnl import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    feed = feedparser.parse(settings.URL)
    count = 0
    stripchars = r'`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    while count < MAX:
        try:
            title = feed.entries[count].title
            if settings.AUTOADVISORY:
                productnames = set()
                for lookupvalue in settings.LOOKUPVALUES:
                    luregex = re.compile('%s' % lookupvalue)
                    matches = luregex.search(title)
                    if matches:
                        for productsplit in settings.PRODUCTSPLIT:
                            if productsplit in title:
                                productname = title.split(productsplit)[1]
                                if ' en ' in productname:
                                    productnames.update(productname.split(' en '))
                                else:
                                    productnames.add(productname)
                for productname in productnames:
                    for channel in settings.ADVISORYCHANS:
                        for lookup in settings.ADVISORYCHANS[channel]:
                            items.append([channel, ' '.join([lookup,productname])])
            link = feed.entries[count].link
            content = settings.NAME + ': ['+title+']('+link+')'
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