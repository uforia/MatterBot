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
import shelve
import sys
import traceback
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
    try:
        if Path(settings.HISTORY).is_file():
            history = shelve.open(settings.HISTORY,writeback=True)
        else:
            if Path('modules/ncscnl/'+settings.HISTORY).is_file():
                history = shelve.open('modules/ncscnl/'+settings.HISTORY,writeback=True)
        if not Path(settings.HISTORY).is_file() and not Path('modules/ncscnl/'+settings.HISTORY).is_file():
            if Path('feed.py').is_file():
                history = shelve.open(settings.HISTORY,writeback=True)
            else:
                if Path('modules/ncscnl/feed.py').is_file():
                    history = shelve.open('modules/ncscnl/'+settings.HISTORY,writeback=True)
        if not 'ncscnl' in history:
            history['ncscnl'] = []
    except Exception as e:
        print(traceback.format_exc())
        raise
    if history:
        while count < MAX:
            try:
                title = feed.entries[count].title
                link = feed.entries[count].link
                content = settings.NAME + ': ['+title+']('+link+')'
                if len(feed.entries[count].description):
                    description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text("\n")).strip().replace('\n','. ')
                    if len(description)>400:
                        description = description[:396]+' ...'
                    content += '\n>'+description+'\n'
                for channel in settings.CHANNELS:
                    pass
                    #items.append([channel, content])
                if settings.AUTOADVISORY:
                    for historyfilter in settings.HISTORYFILTER:
                        historyregex = re.compile('%s' % historyfilter)
                        matches = historyregex.search(title)
                        if matches:
                            historyitem = matches.group(0)
                            if not historyitem in history['ncscnl']:
                                productnames = set()
                                for lookupvalue in settings.LOOKUPVALUES:
                                    luregex = re.compile('%s' % lookupvalue)
                                    matches = luregex.search(title)
                                    if matches:
                                        for productsplit in settings.PRODUCTSPLIT:
                                            if productsplit in title:
                                                productname = title.split(productsplit)[1]
                                                if ' en ' in productname:
                                                    products = productname.split(' en ')
                                                    for product in products:
                                                        productnames.add(product)
                                                else:
                                                    productnames.add(productname)
                                for productname in productnames:
                                    for channel in settings.ADVISORYCHANS:
                                        for lookup in settings.ADVISORYCHANS[channel]:
                                            items.append([channel, ' '.join([lookup,productname])])
                                history['ncscnl'].append(historyitem)
                count+=1
            except IndexError:
                return items # No more items
        return items

if __name__ == "__main__":
    for item in query():
        print(item)
