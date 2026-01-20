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
import requests
import traceback

### Dynamic configuration loader (do not change/edit)
import importlib
import sys
from pathlib import Path
_pkg_name = Path(__file__).parent.name
_module_dir = Path(__file__).parent
if str(_module_dir) not in sys.path:
    sys.path.insert(0, str(_module_dir))
try:
    defaults_mod = importlib.import_module(f'commands.{_pkg_name}.defaults')
except ModuleNotFoundError:
    try:
        defaults_mod = importlib.import_module('defaults')
    except ModuleNotFoundError:
        print(f"Module {_pkg_name} could not be loaded due to a missing default configuration.")
try:
    settings_mod = importlib.import_module(f'commands.{_pkg_name}.settings')
except ModuleNotFoundError:
    try:
        settings_mod = importlib.import_module('settings')
    except ModuleNotFoundError:
        settings_mod = None
settings = {k: v for k, v in vars(defaults_mod).items() if not k.startswith('__')}
if settings_mod:
    settings.update({k: v for k, v in vars(settings_mod).items() if not k.startswith('__')})
from types import SimpleNamespace
settings = SimpleNamespace(**settings)
### Loader end, actual module functionality starts here

def query(MAX=settings.ENTRIES):
    items = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1',
        'Content-type': 'application/rss+xml',
    }
    for category in settings.CATEGORIES:
        try:
            with requests.get("https://www.cshub.com/rss/categories/"+category,headers=headers) as response:
                feed = feedparser.parse(response.content)
                count = 0
                stripchars = '`\\[\\]\'\"'
                regex = re.compile('[%s]' % stripchars)
                while count < MAX:
                    try:
                        title = feed.entries[count].title
                        link = feed.entries[count].link
                        content = settings.NAME + ': [' + title + '](' + link + ')'
                        if len(feed.entries[count].description):
                            description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text("\n")).strip().replace('\n','. ')
                            if len(description)>400:
                                description = description[:396]+' ...'
                            content += '\n>'+description+'\n'
                        for channel in settings.CHANNELS:
                            items.append([channel, content])
                        count+=1
                    except IndexError:
                        return items # No more items
        except Exception as e:
            content = traceback.format_exc()
            for channel in settings.CHANNELS:
                items.append([channel, content])
    return items

if __name__ == "__main__":
    print(query())
