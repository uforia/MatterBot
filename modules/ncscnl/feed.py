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
import traceback



def query(settings=None):
    if settings:
        try:
            from types import SimpleNamespace
            settings = SimpleNamespace(**settings['SETTINGS'])
        except:
            return None
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
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
        while count < settings.ENTRIES:
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
                    items.append([channel, content])
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
                                                if len(settings.TITLEFILTER):
                                                    for titlefilter in settings.TITLEFILTER:
                                                        tfregex = re.compile(re.escape(titlefilter), re.IGNORECASE)
                                                        title = tfregex.sub('',title).strip()
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
                                            items.append([channel, content])
                                            items.append([channel, ' '.join([lookup,productname])])
                                history['ncscnl'].append(historyitem)
                count+=1
            except IndexError:
                return items # No more items
        return items

if __name__ == "__main__":
    for item in query():
        print(item)
