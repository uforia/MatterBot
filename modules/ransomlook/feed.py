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
from pathlib import Path
try:
    from modules.ransomlook import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/ransomlook/settings.py').is_file():
        try:
            from modules.ransomlook import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    count = 0
    stripchars = '`\\[\\]\'\"'
    regex = re.compile(r'[%s]' % stripchars)
    with requests.get(settings.URL+f'/{settings.ENTRIES}') as response:
        if response.status_code in (200,):
            json_response = response.json()
            if len(json_response):
                for post in json_response:
                    group = post['group_name']
                    title = post['post_title']
                    description = post['description']
                    timestamp = post['discovered'].split(".")[0]
                    print(post['screen'])
                    screenshot = urllib.parse.quote(post['screen'].replace(r'\\\\',r'\\'), safe='/<>#')
                    content = settings.NAME + f": `{group}` has posted/claimed `{title}` at `{timestamp}`"
                    if screenshot:
                        if len(screenshot):
                            url = settings.URL.replace('/api/recent','/')+f"{screenshot}"
                            content += f" - Screenshot: [link]({url})"
                    if len(description):
                        description = regex.sub('',description.strip().replace('\n','. '))
                        if len(description)>400:
                            description = description[:396]+" ..."
                        content += "\n>"+description+"\n"
                    for channel in settings.CHANNELS:
                        items.append([channel, content])
                    for keyword in settings.KEYWORDS:
                        keywordchannel = settings.KEYWORDS[keyword]
                        keywordregex = re.compile('%s' % keyword)
                        fullpost = (' '.join((group, title, description))).lower()
                        matches = keywordregex.search(fullpost)
                        if matches:
                            notification = f"@all Keyword `{keyword}` was found in a {content}"
                            items.append([keywordchannel, notification])
                    count+=1
    return items

if __name__ == "__main__":
    print(query())
