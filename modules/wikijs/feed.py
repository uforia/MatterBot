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

import requests

### Dynamic configuration loader (do not change/edit)
import importlib
from pathlib import Path
_pkg_name = Path(__file__).parent.name
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
                    content = settings.NAME + ': ' + link + ' wiki page updated at ' + timestamp + ' UTC'
                    for channel in settings.CHANNELS:
                        items.append([channel, content])
                    count-=1
                except Exception as e:
                    print(e)
                    count-=1
            return items
    except:
        pass

if __name__ == "__main__":
    print(query())
