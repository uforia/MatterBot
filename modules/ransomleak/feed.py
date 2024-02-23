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
import datetime
import re
import requests
import shelve
import ssl
import traceback
import urllib3
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
        except Exception as e:
            print(traceback.format_exc())
            raise
        if history:
            for group in groups:
                ENDPOINT = settings.URL+group
                try:
                    with requests.get(ENDPOINT, auth=authentication) as response:
                        feed = yaml.safe_load(response.content) if response.status_code in (200,301,302,303,307,308) else None
                except yaml.scanner.ScannerError:
                    pass
                if feed:
                    entries = sorted(feed, key=lambda feed: feed['published'], reverse=True)[:MAX]
                    for entry in entries:
                        item = ''
                        for field in fields:
                            if field in entry:
                                value = regex.sub(' ', entry[field]).strip()
                                if field == 'group':
                                    if value in settings.RENAMES:
                                        value = settings.RENAMES[value]
                                if field == 'company':
                                    if len(entry['domain'].strip()) and not len(entry['company']):
                                        domain = entry['domain'].strip()
                                        if not 'http' in domain:
                                            url = 'https://'+domain
                                        else:
                                            url = domain
                                        try:
                                            headers = {
                                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
                                                'accept': 'application/json, text/plain, */*',
                                                'accept-language': 'en-US,en;q=0.9,hi;q=0.8,de;q=0.7,ur;q=0.6,pa;q=0.5,es;q=0.4'
                                            }
                                            session = requests.Session()
                                            session.max_redirects = 3
                                            session.headers = headers
                                            session.verify = False
                                            with session.get(url,allow_redirects=False,timeout=10) as response:
                                                session.cookies.update(session.cookies)
                                            with session.get(url,allow_redirects=False,timeout=10) as response:
                                                if response.status_code in (200, 301, 302, 303, 307, 308):
                                                    content = session.get(url).text
                                                    html = bs4.BeautifulSoup(content,"lxml")
                                                    value = regex.sub('',html.title.text)
                                                    value = value.replace('\\n','').replace('\\r','').strip()
                                                else:
                                                    value = '*Error '+str(response.status_code)+'*'
                                        except requests.exceptions.TooManyRedirects:
                                            value = '*Redirects Exceeded*'
                                        except requests.exceptions.Timeout:
                                            value = '*Timeout*'
                                        except:
                                            value = '*Unknown Error*'
                                    else:
                                        value = '`'+value+'`'
                                if field == 'size':
                                    if len(entry['released']) and not len(entry['size']):
                                        value = '*Unclear*'
                                if len(value):
                                    if field == 'domain':
                                        if re.search(r"^(((?!\-))(xn\-\-)?[a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9]{1,1}\.)*(xn\-\-)?([a-zA-Z0-9\-]{1,61}|[a-zA-Z0-9\-]{1,30})\.[a-zA-Z]{2,}$", value) or 'http' in value:
                                            value = '[%s](%s)' % (value,value)
                                else:
                                    if field == 'published':
                                        if not len(entry[field]):
                                            value = '%date%'
                                        else:
                                            value = entry[field]
                                    else:
                                        value = '-'
                            item += '| %s ' % (value,)
                        item += '|'
                        items.append(item)
            if len(items):
                count = 0
                table = '**%s Update**\n\n' % (settings.NAME,)
                for field in fields:
                    table += '| %s ' % (fields[field])
                table += '|\n'
                for field in fields:
                    if field in ('published','released','size'):
                        table += '| -: '
                    else:
                        table += '| :- '
                table += '|\n'
                for item in items:
                    historyitem = item.replace('%date%','-')
                    if not historyitem in history['ransomleak']:
                        count += 1
                        today = datetime.datetime.now().strftime('%Y-%m-%d')
                        history['ransomleak'].append(historyitem)
                        table += item.replace('%date%',today)+'\n'
                table += '\n\n'
                if count>0:
                    messages.append(table)
    except Exception as e:
        print(traceback.format_exc())
        message = "An error occurred during the Ransomleaks feed parsing:\n%s" % str(traceback.format_exc())
    finally:
        for message in messages:
            for channel in settings.CHANNELS:
                announcements.append([channel,message])
        return announcements

if __name__ == "__main__":
    print(query())
