#!/usr/bin/env python3

# Every module must set the CHANNEL variable to indicate where information should be sent to in Mattermost
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

import requests
import traceback
import yaml
from pathlib import Path
try:
    from modules.ransomleak import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/ransomleak/settings.py').is_file():
        try:
            from modules.ransomleak import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    if settings.AUTH['username'] and settings.AUTH['password']:
        authentication = (settings.AUTH['username'],settings.AUTH['password'])
    try:
        for group in settings.GROUPS:
            ENDPOINT = settings.URL+group+'.json'
            with requests.get(ENDPOINT, auth=authentication) as response:
                feed = yaml.safe_load(response.content)
            entries = sorted(feed, key=lambda feed: feed['scrape'], reverse=True)[-MAX:]
            for entry in entries:
                group = entry['group']
                date = entry['published']
                scrape = entry['scrape']
                victim = entry['company']
                size = '`'+entry['size']+'`' if 'size' in entry else 'an unknown amount'
                content = settings.NAME + ': Actor **%s**' % (group,)
                content += ' has leaked %s of data' % (size,)
                content += ' from victim **%s**' % (victim,)
                if date == 'unknown':
                    content += ' possibly at `%s`' % (scrape,)
                else:
                    content += ' at `%s`' % (date,)
                items.append([settings.CHANNEL, content])
    except Exception as e:
        print(traceback.format_exc())
        content = "An error occurred during the Ransomleaks feed parsing."
        items.append([settings.CHANNEL,content])
    finally:
        return items

if __name__ == "__main__":
    print(query())
