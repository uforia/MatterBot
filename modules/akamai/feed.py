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

import os
import sys

import feedparser

try:
    from feedutils import clean_description, load_settings
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from feedutils import clean_description, load_settings


def query(settings=None):
    settings = load_settings(settings)
    items = []
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
    count = 0
    while count < settings.ENTRIES:
        try:
            title = feed.entries[count].title
            link = feed.entries[count].link
            if "security" in link:
                content = settings.NAME + ': [' + title + '](' + link + ')'
                if len(feed.entries[count].description):
                    content += '\n>' + clean_description(feed.entries[count].description) + '\n'
                for channel in settings.CHANNELS:
                    items.append([channel, content])
            count += 1
        except IndexError:
            return items # No more items
    return items

if __name__ == "__main__":
    print(query())
