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
import traceback

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here

def query(MAX=settings.ENTRIES):
    items = []
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'MatterBot Feed Automation 1.0',
    }
    try:
        for category in settings.CATEGORIES:
            feedurl = settings.CATEGORIES[category]
            with requests.get(feedurl, headers=headers) as response:
                if response.status_code in (200,204):
                    json_response = response.json()
                    for vulnerability in json_response:
                        id = vulnerability['id']
                        description = vulnerability['description']
                        if len(description):
                            description = regex.sub('',bs4.BeautifulSoup(description,'lxml').get_text("\n")).strip().replace('\n','. ')
                            if len(description)>400:
                                description = description[:396]+' ...'
                        cat = category.split('/')[-1].replace('-',' ').title()
                        cvss = vulnerability['baseScore']
                        link = settings.BASEDETAILURL+id
                        content = f"{settings.NAME} - {cat}: [{id}]({link}) - CVSS: {cvss}"
                        content += '\n>'+description+'\n'
                        for channel in settings.CHANNELS:
                            items.append([channel, content])
                else:
                    content = f"An error occurred pulling the EUVD {category} feed: {response.content} ({response.status_code})"
                    items.append([channel, content])
    except Exception as e:
        content = "A Python error occurred in the EUVD module: `%s`\n```%s```\n" % (str(e), traceback.format_exc())
        items.append([channel, content])
    finally:
        return items

if __name__ == "__main__":
    print(query())
