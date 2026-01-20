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
import urllib.parse

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
    count = 0
    stripchars = '\r\n|`\\[\\]\'\"'
    regex = re.compile(r'[%s]' % stripchars)
    with requests.get(settings.URL+f'/{settings.ENTRIES}') as response:
        if response.status_code in (200,):
            json_response = response.json()
            if len(json_response):
                for post in json_response:
                    group = post['group_name']
                    title = regex.sub('. ',post['post_title'])
                    title = re.sub(r'(\. ){2,}', '. ', title)
                    description = regex.sub('. ',post['description'])
                    description = re.sub(r'(\. ){2,}', '. ', description)
                    timestamp = post['discovered'].split(".")[0]
                    screen = post['screen'] if 'screen' in post else None
                    upload = None
                    content = settings.NAME + f": `{group}` has posted/claimed `{title}` at `{timestamp}`"
                    if screen:
                        screenshot = urllib.parse.quote(post['screen'].replace(r'\\\\',r'\\'), safe='/<>#')
                        if len(screenshot):
                            url = settings.URL.replace('/api/recent','/')+f"{screenshot}"
                            if not settings.SCREENDL:
                                content += f" - Screenshot: [link]({url})"
                            else:
                                with requests.get(url) as scrdl:
                                    if scrdl.status_code in (200,):
                                        for header in scrdl.headers:
                                            if header.lower() == 'content-disposition':
                                                filename = urllib.parse.unquote_plus(re.findall('filename=(.+)', scrdl.headers[header], re.IGNORECASE)[0]).replace('?','-').replace('"','')
                                                bytes = scrdl.content
                                        upload = {'filename': filename, 'bytes': bytes}
                    if len(description)>400:
                        description = description[:396]+" ..."
                    if len(description):
                        content += "\n>"+description+"\n"
                    for channel in settings.CHANNELS:
                        if upload:
                            items.append([channel, content, {'uploads': [upload]}])
                        else:
                            items.append([channel, content])
                    for keyword in settings.KEYWORDS:
                        keywordchannel = settings.KEYWORDS[keyword]
                        keywordregex = re.compile('%s' % keyword)
                        fullpost = (' '.join((group, title, description))).lower()
                        matches = keywordregex.search(fullpost)
                        if matches:
                            notification = f"@all Keyword `{keyword}` was found in a {content}"
                            if upload:
                                items.append([keywordchannel, notification, {'uploads': [upload]}])
                            else:
                                items.append([keywordchannel, notification])
                    count+=1
    return items

if __name__ == "__main__":
    print(query())
