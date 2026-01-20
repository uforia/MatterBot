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
import os
import sys



def importScore():
    running = os.path.abspath(__file__)
    cwd = os.path.abspath(os.path.join(os.path.dirname(running), '..'))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    from opencve.defaults import ADVISORYTHRESHOLD # Import threshold score from opencve module
    return ADVISORYTHRESHOLD

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
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    while count < settings.ENTRIES:
        try:
            title = feed.entries[count].title
            link = feed.entries[count].link
            content = settings.NAME + ': [' + title + '](' + link + ')'
            if len(feed.entries[count].description):
                description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text("\n")).strip().replace('\n','. ')
                try:
                    index = description.index('CVSS Score:') + 12
                    cvss = description[index:index+3]
                    cvss = float(cvss)
                    if len(description)>400:
                        description = description[:396]+' ...'
                    content += '\n>'+description+'\n'
                    if cvss >= importScore():
                        for channel in settings.CHANNELS:
                            items.append([channel, content])
                except ValueError:
                    count+=1
            count+=1
        except IndexError:
            return items # No more items
    return items

if __name__ == "__main__":
    print(query())
