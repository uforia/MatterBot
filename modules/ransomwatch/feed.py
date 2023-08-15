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

import html
import re
import requests
import traceback
from pathlib import Path
try:
    from modules.ransomwatch import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/ransomwatch/settings.py').is_file():
        try:
            from modules.ransomwatch import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    try:
        with requests.get(settings.URL) as response:
            feed = response.json()
        entries = sorted(feed, key=lambda feed: feed['discovered'], reverse=True)[:MAX]
        if len(entries):
            content = '**Ransomware Activity Update**\n'
            content += '\n| **Group** | **Victim** | **Publication** |'
            content += '\n| :- | :- | -: |'
            for entry in entries:
                victim = entry['post_title'].replace('&amp;','&').replace('&amp;','&').strip('\r\n')
                group = entry['group_name'].replace('&amp;','&').replace('&amp;','&').strip('\r\n').title()
                date = entry['discovered'].split('.')[0].strip(' \r\n')
                if re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", victim) or 'http' in victim:
                    victim = '[%s](%s)' % (victim, victim)
                else:
                    victim = victim.title()
                content += '\n| %s | %s | %s |' % (group, victim, date)
            content += '\n\n'
            for channel in settings.CHANNELS:
                items.append([channel, content])
    except Exception as e:
        content = "An error occurred during the Ransomwatch feed parsing: %s\n%s" % (str(e),traceback.format_exc())
        for channel in settings.CHANNELS:
            items.append([channel,content])
    finally:
        return items

if __name__ == "__main__":
    print(query())
