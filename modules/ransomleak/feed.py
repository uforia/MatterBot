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

import re
import requests
import traceback
import yaml
from bs4 import BeautifulSoup
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
        ENDPOINT = settings.URL
        with requests.get(ENDPOINT, auth=authentication) as response:
            soup = BeautifulSoup(response.text,'html.parser')
            groups = [node.get('href') for node in soup.find_all('a') if node.get('href').endswith('.json')]
        for group in groups:
            ENDPOINT = settings.URL+'/'+group
            with requests.get(ENDPOINT, auth=authentication) as response:
                feed = yaml.safe_load(response.content)
            if len(feed)>0:
                entries = sorted(feed, key=lambda feed: feed['scrape'], reverse=True)[:MAX]
                for entry in entries:
                    group = entry['group'].strip()
                    if 'published' in entry:
                        date = entry['published'].strip()
                        if not len(date):
                            date = 'unknown'
                    else:
                        date = 'unknown'
                    scrape = entry['scrape'].strip()
                    if 'company' in entry:
                        victim = entry['company'].strip()
                    else:
                        victim = None
                    if 'domain' in entry:
                        domain = entry['domain'].strip()
                        if re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", domain) or 'http' in domain:
                            if victim:
                                victim = '[%s](%s)' % (victim,domain)
                            else:
                                victim = '[%s](%s)' % (domain,domain)
                    else:
                        if victim:
                            if re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", domain) or 'http' in victim:
                                victim = '[%s](%s)' % (victim,victim)
                            else:
                                victim = '**%s**' % (victim,)
                        else:
                            victim = '`an unknown company`'
                    size = '`'+entry['size'].strip()+'`' if 'size' in entry else 'an unknown amount'
                    content = settings.NAME + ': Actor **%s**' % (group,)
                    content += ' has leaked %s of data' % (size,)
                    content += ' from victim %s' % (victim,)
                    if date == 'unknown':
                        content += ' at an unknown date.'
                    else:
                        content += ' at `%s`.' % (date,)
                    for channel in settings.CHANNELS:
                        items.append([channel, content])
    except Exception as e:
        print(traceback.format_exc())
        content = "An error occurred during the Ransomleaks feed parsing."
        for channel in settings.CHANNELS:
            items.append([channel,content])
    finally:
        return items

if __name__ == "__main__":
    print(query())
