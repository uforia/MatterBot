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
    from modules.reddit import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/reddit/settings.py').is_file():
        try:
            from modules.reddit import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    stripchars = '`\[\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    for subreddit in settings.SUBREDDITS:
        feed = feedparser.parse("https://www.reddit.com/r/"+subreddit+"/.rss")
        count = 0
        while count < MAX:
            try:
                title = feed.entries[count].title
                link = feed.entries[count].link
                content = 'Reddit post in [/r/' + subreddit + '](https://www.reddit.com/r/'+subreddit+'): [' + title + '](' + link + ')'
                if 'description' in feed.entries[count]:
                    description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text())
                    if len(description)>320:
                        description = description[:316]+' ...'
                    content += '\n```\n'+description+'\n```\n'
                for channel in settings.CHANNELS:
                    items.append([channel, content])
                count+=1
            except IndexError:
                return items # No more items
    return items

if __name__ == "__main__":
    print(query())
