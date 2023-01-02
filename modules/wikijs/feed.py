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
from pathlib import Path
from pathlib import Path
try:
    from modules.wikijs import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/wikijs/settings.py').is_file():
        try:
            from modules.wikijs import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=0):
    items = []
    query = '{"query":"query{pages { list(orderBy:UPDATED) { path title updatedAt }}}"}'
    try:
        response = requests.post(
            settings.API + '/graphql',
            data = query,
            headers = { 'Authorization': 'Bearer ' + settings.TOKEN,
                        'Content-Type': 'application/json',
                      },
        )
        if response.status_code == 200:
            items = []
            json = response.json()['data']['pages']['list']
            count = len(json)-1
            while count > 0:
                try:
                    timestamp = json[count]['updatedAt'].split('T')[1][:8]
                    url = settings.API + '/' + json[count]['path']
                    title = json[count]['title']
                    link = '**[' + title + '](' + url + ')**'
                    content = settings.WIKINAME + ' ' + link + ' wiki page updated at ' + timestamp + ' UTC'
                    items.append([settings.CHANNEL, content])
                    count-=1
                except Exception as e:
                    print(e)
                    count-=1
            return items
    except:
        pass

if __name__ == "__main__":
    print(query())
