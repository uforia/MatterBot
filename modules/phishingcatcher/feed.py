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
import re
import requests
import shelve
import traceback
from pathlib import Path

try:
    from modules.phishingcatcher import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/phishingcatcher/settings.py').is_file():
        try:
            from modules.phishingcatcher import settings
        except ModuleNotFoundError: # local test run
            import settings

def read_data_from_file(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
    return data

def query(MAX=settings.ENTRIES):
    items = []
    data = None
    count = 0
    stripchars = '`\\[\\]\'\"\(\)'
    regex = re.compile('[%s]' % stripchars)
    if 'http' in settings.SUSLOG.lower():
        if settings.AUTH['username'] and settings.AUTH['password']:
            authentication = (settings.AUTH['username'],settings.AUTH['password'])
        else:
            authentication = ()
        with requests.get(settings.SUSLOG, auth=authentication) as response:
            if response.status_code in (200,301,302,303,307,308):
                data = response.content.decode('utf-8').split('\n')
            else:
                data = None
    else:
        suslog = Path(settings.SUSLOG)
        if suslog.is_file():
            with open(suslog, 'r') as f:
                data = set(f.readlines())
    if data:
        try:
            if Path(settings.HISTORY).is_file():
                history = shelve.open(settings.HISTORY,writeback=True)
            else:
                if Path('modules/phishingcatcher/'+settings.HISTORY).is_file():
                    history = shelve.open('modules/phishingcatcher/'+settings.HISTORY,writeback=True)
            if not Path(settings.HISTORY).is_file() and not Path('modules/phishingcatcher/'+settings.HISTORY).is_file():
                if Path('feed.py').is_file():
                    history = shelve.open(settings.HISTORY,writeback=True)
                else:
                    if Path('modules/phishingcatcher/feed.py').is_file():
                        history = shelve.open('modules/phishingcatcher/'+settings.HISTORY,writeback=True)
            if not 'phishingcatcher' in history:
                history['phishingcatcher'] = []
        except Exception as e:
            print(traceback.format_exc())
            raise
        suspicious_domains = []
        for line in data:
            if any(domain in line.strip() for domain in settings.DOMAINS):
                domain, score = regex.sub('',line).strip().replace('.','[.]',1).split(' ')
                suspicious_domains.append((domain,score.split('=')[1]))
        if len(suspicious_domains):
            entries = 0
            count = 0
            content = ""
            while count < len(suspicious_domains):
                domain, score = suspicious_domains[count]
                if not domain in history['phishingcatcher']:
                    history['phishingcatcher'].append(domain)
                    if int(score) > int(settings.THRESHOLD):
                        content += '\n| `%s` | `%s` |' % (score, domain)
                        entries += 1
                count += 1        
            if entries > 0:
                message = "\n**PhishingCatcher** found `%d` new potential phishing domain(s):\n" % (entries,)
                message += "\n| **Score** | **Domain** |"
                message += "\n| -: | :- |"
                message += content
                message += '\n\n'
                for channel in settings.CHANNELS:
                    items.append([channel, message])
    return items

if __name__ == "__main__":
    print(query())
