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
from pathlib import Path

try:
    from modules.certfr import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/certfr/settings.py').is_file():
        try:
            from modules.certfr import settings
        except ModuleNotFoundError: # local test run
            import settings


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