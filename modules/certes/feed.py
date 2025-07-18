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
    from modules.certes import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/certes/settings.py').is_file():
        try:
            from modules.certes import settings
        except ModuleNotFoundError: # local test run
            import settings


def query(MAX=settings.ENTRIES):
    items = []
    for URL in settings.URLS:
        feed = feedparser.parse(URL, agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
        count = 0
        stripchars = '`\\[\\]\'\"'
        regex = re.compile('[%s]' % stripchars)
        while count < MAX:
            try:
                title = feed.entries[count].title
                if settings.TRANSLATION:
                    from_lan = "es"
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
                link = feed.entries[count].link
                content = settings.NAME + ': [' + title + '](' + link + ')'
                for channel in settings.CHANNELS:
                    items.append([channel, content])
                count+=1
            except IndexError:
                return items # No more items
    return items

if __name__ == "__main__":
    print(query())
