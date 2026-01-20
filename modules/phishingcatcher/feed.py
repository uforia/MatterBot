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
import shelve
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

def read_data_from_file(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
    return data

def query(MAX=settings.ENTRIES):
    items = []
    data = None
    count = 0
    stripchars = r'`\\[\\]\'\"\(\)'
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
                score = score.replace(')','')
                if not domain in history['phishingcatcher']:
                    history['phishingcatcher'].append(domain)
                    try:
                        if int(score) > int(settings.THRESHOLD):
                            content += '\n| `%s` | `%s` |' % (score, domain)
                            entries += 1
                    except:
                        print(score,domain)
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
