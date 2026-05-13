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
import html
import ipaddress
import re
import requests
import socket
from urllib.parse import urlparse


def _safe_fetch(url, headers, max_bytes=5 * 1024 * 1024):
    """SSRF-guarded HTTPS GET for upstream-RSS-controlled media URLs.

    Returns the response body bytes on success, or None on any refusal
    (non-https scheme, unresolvable host, private/loopback/link-local/
    multicast/reserved IP, redirect, non-200/206 status, body over the
    cap, transport exception). No partial bodies are returned: oversize
    responses are dropped entirely so a hostile feed cannot exfiltrate
    a giant payload through a media-attachment channel post.
    """
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        return None
    try:
        resolved = socket.gethostbyname(parsed.hostname)
        host_ip = ipaddress.ip_address(resolved)
    except (socket.gaierror, ValueError):
        return None
    if (host_ip.is_private or host_ip.is_loopback or host_ip.is_link_local
            or host_ip.is_multicast or host_ip.is_reserved or host_ip.is_unspecified):
        return None
    try:
        with requests.get(url, headers=headers, timeout=(10, 30),
                          allow_redirects=False, stream=True) as r:
            if r.status_code not in (200, 206):
                return None
            chunks = []
            total = 0
            for chunk in r.iter_content(chunk_size=64 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    return None
                chunks.append(chunk)
            return b''.join(chunks)
    except Exception:
        return None


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
    MAXENTRIES = settings.ENTRIES * len(settings.URLS)
    for url in settings.URLS:
        title = url
        feed = feedparser.parse(settings.URLS[url], agent=user_agent)
        count = 0
        stripchars = '\\[\\]\'\"'
        regex = re.compile('[%s]' % stripchars)
        while count < settings.ENTRIES:
            try:
                link = feed.entries[count].link
                content = bs4.BeautifulSoup(html.unescape(settings.NAME), 'html.parser').get_text() + ': [' + title + '](' + link + ')'
                if len(feed.entries[count].description):
                    description = regex.sub('',bs4.BeautifulSoup(html.unescape(feed.entries[count].description),'html.parser').get_text()).replace('```json','\n```json\n')
                    if len(description)>400:
                        description = description[:396]+' ...'
                    content += '\n>'+description+'\n'
                upload = None
                if 'media_content' in feed.entries[count]:
                    uploads = []
                    for media in feed.entries[count]['media_content']:
                        if 'url' in media:
                            url = media['url']
                            content = _safe_fetch(url, headers)
                            if content is not None:
                                filename = url.split('/')[-1]
                                upload = {'filename': filename, 'bytes': content}
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
