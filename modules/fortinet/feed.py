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
import os
import re
import requests
import sys



def importScore():
    running = os.path.abspath(__file__)
    cwd = os.path.abspath(os.path.join(os.path.dirname(running), '..'))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    from opencve.defaults import ADVISORYTHRESHOLD # Import threshold score from opencve module
    return ADVISORYTHRESHOLD

def checkPage(link):
    try: # Check if feed url contains CVSS property on page
        with requests.Session() as session:
            response = session.get(link, headers={'User-Agent': 'MatterBot RSS Automation 1.0'})
            response.raise_for_status()
            data = bs4.BeautifulSoup(response.content, "html.parser")
            selection = [ # Check if feed url contains CVSS property on page, based on feeds
                'table.outbreak-alert-table tr',
                'td a[href^=" https://nvd.nist.gov/"]'
            ]
            for page in selection:
                matches = data.select(page)
                if page[0]: # Get seperate value from table using filter
                    for row in matches:
                        columns = row.find_all("td")
                        if len(columns) >= 3 and "CVSS Rating" in columns[1].text:
                            tableScore = columns[2].text.strip()
    except requests.exceptions.RequestException:
        matches = False
    try: # Return dynamic values
        return matches, tableScore
    except NameError:
        return matches

def pageScore(matches):
    # checkPage() has three possible return shapes: False (the page did not load),
    # a (selection, tableScore) tuple, or a bare list of score elements. Collapse
    # them into "the highest CVSS score found on the page, or None if there is
    # none" so the caller has a single thing to compare against the threshold.
    if not matches:
        return None
    if isinstance(matches, tuple):
        candidates = [matches[1]]
    else:
        candidates = [score.text for score in matches]
    scores = []
    for candidate in candidates:
        try:
            scores.append(float(str(candidate).strip()))
        except (TypeError, ValueError): # Not a score: e.g. a table header cell
            continue
    return max(scores) if scores else None

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
    for URL in settings.URLS:
        feed = feedparser.parse(str(URL), agent='MatterBot RSS Automation 1.0')
        count = 0
        stripchars = '`\\[\\]\'\"'
        regex = re.compile('[%s]' % stripchars)
        while count < settings.ENTRIES:
            try:
                title = feed.entries[count].title
                link = feed.entries[count].link
                content = None
                if settings.FILTER:
                    THRESHOLD = importScore()
                    # FILTER means "only post advisories that meet the threshold", so an
                    # advisory whose severity we cannot establish -- no CVSS on the page,
                    # or the page did not load -- is skipped. It is not evidence of a
                    # severe advisory, and posting it defeats the setting.
                    cvss = pageScore(checkPage(link))
                    if cvss is not None and cvss >= THRESHOLD:
                        content = settings.NAME + ': [' + title
                        content += f' - CVSS: `{cvss}`'
                        content += '](' + link + ')'
                else:
                    content = settings.NAME + ': [' + title + '](' + link + ')'
                if content is None: # Entry did not pass the filter: skip it. Never fall through -- content
                    count+=1        # still holds the *previous* entry, which would be posted a second time.
                    continue
                if len(feed.entries[count].description):
                    description = regex.sub('',bs4.BeautifulSoup(feed.entries[count].description,'lxml').get_text("\n")).strip().replace('\n','. ')
                    if len(description)>400:
                        description = description[:396]+' ...'
                    content += '\n>'+description+'\n'
                for channel in settings.CHANNELS:
                    items.append([channel, content])
                count+=1
            except IndexError:
                return items # No more items
    return items

if __name__ == "__main__":
    print(query())
