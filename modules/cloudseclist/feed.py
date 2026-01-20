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



def query(settings=None):
    if settings:
        try:
            from types import SimpleNamespace
            settings = SimpleNamespace(**settings['SETTINGS'])
        except:
            return None
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
    count = 0
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    while count < settings.ENTRIES:
        try:
            title = feed.entries[count].title
            link = feed.entries[count].link
            content = settings.NAME + ': [Cloudseclist ' + title[21:] + '](' + link + ')'
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
