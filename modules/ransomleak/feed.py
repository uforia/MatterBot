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

import collections
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
    stripchars = '`\n\r\'\"\|'
    regex = re.compile('[%s]' % stripchars)
    if settings.AUTH['username'] and settings.AUTH['password']:
        authentication = (settings.AUTH['username'],settings.AUTH['password'])
    try:
        ENDPOINT = settings.URL
        with requests.get(ENDPOINT, auth=authentication) as response:
            soup = BeautifulSoup(response.text,'html.parser')
            groups = [node.get('href') for node in soup.find_all('a') if node.get('href').endswith('.json')]
        for group in groups:
            fields = collections.OrderedDict({
                'group': 'Group',
                'company': 'Victim',
                'domain': 'URL',
                'published': 'Publication',
                'released': 'Leak Date',
                'size': 'Size',
            })
            ENDPOINT = settings.URL+'/'+group
            with requests.get(ENDPOINT, auth=authentication) as response:
                feed = yaml.safe_load(response.content)
            if len(feed)>0:
                entries = sorted(feed, key=lambda feed: feed['published'], reverse=True)[:MAX]
                for entry in entries:
                    message = ''
                    for field in fields:
                        message += '| %s ' % (fields[field])
                    message += '|\n'
                    for field in fields:
                        if field in ('published','released','size'):
                            message += '| -: '
                        else:
                            message += '| :- '
                    message += '|\n'
                    for field in fields:
                        if field in entry:
                            value = regex.sub(' ', entry[field]).strip()
                            if field == 'size':
                                if len(entry['released']) and not len(entry['size']):
                                    value = 'Unclear'
                            if len(value):
                                if field == 'domain':
                                    if re.search(r"^(((?!\-))(xn\-\-)?[a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9]{1,1}\.)*(xn\-\-)?([a-zA-Z0-9\-]{1,61}|[a-zA-Z0-9\-]{1,30})\.[a-zA-Z]{2,}$", value) or 'http' in value:
                                        value = '[%s](%s)' % (value,value)
                            else:
                                value = '-'
                            message += '| %s ' % (value,)
                    message += '|\n\n\n'
                    for channel in settings.CHANNELS:
                        items.append([channel,message])
    except Exception as e:
        message = "An error occurred during the Ransomleaks feed parsing:\n%s" % str(traceback.format_exc())
        for channel in settings.CHANNELS:
            items.append([channel,message])
    finally:
        return items

if __name__ == "__main__":
    print(query())
