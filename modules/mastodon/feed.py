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



def query(settings=None):
    if settings:
        try:
            from types import SimpleNamespace
            settings = SimpleNamespace(**settings)
        except:
            pass
    else:
        import defaults as settings
        try:
            import settings as _override
            settings.__dict__.update({k: v for k, v in vars(_override).items() if not k.startswith('__')})
        except ImportError:
            pass
    items = []
    user_agent = 'MatterBot RSS Automation 1.0'
    headers = {
        'Content-Type': 'text/json',
        'User-Agent': f"{user_agent}",
    }
    for url in settings.URLS:
        title = url
        feed = feedparser.parse(settings.URLS[url], agent=user_agent)
        count = 0
        stripchars = '`\\[\\]\'\"'
        regex = re.compile('[%s]' % stripchars)
        while count < settings.ENTRIES:
            try:
                link = feed.entries[count].link
                content = settings.NAME + ': [' + title + '](' + link + ')'
                if len(feed.entries[count].description):
                    description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text("\n")).strip().replace('\n','. ')
                    if len(description)>400:
                        description = description[:396]+' ...'
                    content += '\n>'+description+'\n'
                upload = None
                if 'media_content' in feed.entries[count]:
                    uploads = []
                    for media in feed.entries[count]['media_content']:
                        if 'url' in media:
                            url = media['url']
                            with requests.get(url, headers=headers) as response:
                                if response.status_code in (200,206):
                                    filename = url.split('/')[-1]
                                    bytes = response.content
                                    upload = {'filename': filename, 'bytes': bytes}
                                    uploads.append(upload)
                for channel in settings.CHANNELS:
                    if upload:
                        items.append([channel, content, {'uploads': uploads}])
                    else:
                        items.append([channel, content])
                count+=1
            except IndexError:
                return items # No more items
    return items

if __name__ == "__main__":
    print(query())
