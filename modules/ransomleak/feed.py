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
import collections
import re
import requests
import shelve
import sys
import traceback
import yaml
from bs4 import BeautifulSoup
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
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
    announcements = []
    stripchars = '`\t\n\r\'\"\|'
    regex = re.compile('[%s]' % stripchars)
    if settings.AUTH['username'] and settings.AUTH['password']:
        authentication = (settings.AUTH['username'],settings.AUTH['password'])
    try:
        ENDPOINT = settings.URL
        with requests.get(ENDPOINT, auth=authentication) as response:
            soup = BeautifulSoup(response.text,features='lxml')
            groups = [node.get('href') for node in soup.find_all('a') if node.get('href').endswith('.json')]
        fields = collections.OrderedDict({
            'group': 'Group',
            'company': 'Victim',
            'domain': 'URL',
            'published': 'Publication',
            'released': 'Leak Date',
            'size': 'Size',
        })
        items = []
        for group in groups:
            ENDPOINT = settings.URL+'/'+group
            with requests.get(ENDPOINT, auth=authentication) as response:
                feed = yaml.safe_load(response.content)
            if len(feed)>0:
                entries = sorted(feed, key=lambda feed: feed['published'], reverse=True)[:MAX]
                for entry in entries:
                    item = ''
                    for field in fields:
                        if field in entry:
                            value = regex.sub(' ', entry[field]).strip()
                            if field == 'company':
                                if len(entry['domain'].strip()) and not len(entry['company']):
                                    domain = entry['domain'].strip()
                                    if not 'http' in domain:
                                        url = 'https://'+domain
                                    else:
                                        url = domain
                                    try:
                                        headers = {
                                            'Host': domain,
                                            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1',
                                        }
                                        session = requests.Session()
                                        session.max_redirects = 2
                                        session.headers = headers
                                        session.verify = False
                                        with session.get(url,verify=False,allow_redirects=True,timeout=5) as response:
                                            session.cookies.update(session.cookies)
                                        with session.get(url,verify=False,allow_redirects=True,timeout=5) as response:
                                            if response.status_code == 200:
                                                html = bs4.BeautifulSoup(response.text,"lxml")
                                                value = regex.sub('-',html.title.text).strip()
                                            else:
                                                value = '*Error '+str(response.status_code)+'*'
                                    except requests.exceptions.TooManyRedirects:
                                        value = '*Redirects Exceeded*'
                                    except requests.exceptions.Timeout:
                                        value = '*Timeout*'
                                    except:
                                        value = '*Unknown Error*'
                            if field == 'size':
                                if len(entry['released']) and not len(entry['size']):
                                    value = '*Unclear*'
                            if len(value):
                                if field == 'domain':
                                    if re.search(r"^(((?!\-))(xn\-\-)?[a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9]{1,1}\.)*(xn\-\-)?([a-zA-Z0-9\-]{1,61}|[a-zA-Z0-9\-]{1,30})\.[a-zA-Z]{2,}$", value) or 'http' in value:
                                        value = '[%s](%s)' % (value,value)
                            else:
                                value = '-'
                        item += '| %s ' % (value,)
                    item += '|'
                    items.append(item)
        messages = []
        try:
            if Path(settings.HISTORY).is_file():
                history = shelve.open(settings.HISTORY,writeback=True)
            else:
                if Path('modules/ransomleak/'+settings.HISTORY).is_file():
                    history = shelve.open('modules/ransomleak/'+settings.HISTORY,writeback=True)
            if not Path(settings.HISTORY).is_file() and not Path('modules/ransomleak/'+settings.HISTORY).is_file():
                if Path('feed.py').is_file():
                    history = shelve.open(settings.HISTORY,writeback=True)
                else:
                    if Path('modules/ransomleak/feed.py').is_file():
                        history = shelve.open('modules/ransomleak/'+settings.HISTORY,writeback=True)
            if not 'ransomleak' in history:
                history['ransomleak'] = []
            for item in items:
                if not item in history['ransomleak']:
                    history['ransomleak'].append(item)
                    messages.append(item)
            history.sync()
            history.close()
        except:
            raise
        if len(messages):
            announcements = []
            table = ''
            for field in fields:
                table += '| %s ' % (fields[field])
            table += '|\n'
            for field in fields:
                if field in ('published','released','size'):
                    table += '| -: '
                else:
                    table += '| :- '
            table += '|\n'
            for message in messages:
                table += message
                table += '\n'
            table += '\n\n'
            for channel in settings.CHANNELS:
                announcements.append([channel,table])
    except Exception as e:
        message = "An error occurred during the Ransomleaks feed parsing:\n%s" % str(traceback.format_exc())
        for channel in settings.CHANNELS:
            announcements.append([channel,message])
    finally:
        return announcements

if __name__ == "__main__":
    print(query())
