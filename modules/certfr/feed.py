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

from argostranslate import package, translate
import feedparser
import re

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

def query(MAX=settings.ENTRIES):
    items = []
    feed = feedparser.parse(settings.URL, agent='MatterBot RSS Automation 1.0')
    reversedFeed = list(reversed(feed.entries))
    count = 0
    stripchars = '`\\[\\]\'\"'
    regex = re.compile('[%s]' % stripchars)
    while count < MAX:
        try:
            title = reversedFeed[count].title
            if settings.TRANSLATION:
                from_lan = "fr"
                to_lan = "en"
                # Check for new language packages to install (initial setup)
                installed_packages = package.get_installed_packages()
                package.update_package_index()
                updateIndex = package.get_available_packages()
                # Filter for correct language packages
                packageSelection = next(filter(lambda x: x.from_code == from_lan and x.to_code == to_lan, updateIndex))
                if packageSelection not in installed_packages:
                    package.install_from_path(packageSelection.download())
                title = translate.translate(title, from_lan, to_lan)
            link = reversedFeed[count].link
            content = settings.NAME + ': [' + title + '](' + link + ')'
            for channel in settings.CHANNELS:
                items.append([channel, content])
            count+=1
        except IndexError:
            return items # No more items
    return items

if __name__ == "__main__":
    print(query())