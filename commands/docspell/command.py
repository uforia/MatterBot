#!/usr/bin/env python3

import datetime
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.docspell import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/docspell/settings.py').is_file():
        try:
            from commands.docspell import settings
        except ModuleNotFoundError: # local test run
            import settings


def getToken():
    auth = {
        'account': settings.APIURL['docspell']['username'],
        'password': settings.APIURL['docspell']['password'],
        'rememberMe': True,
    }
    headers = {
        'Content-Type': settings.CONTENTTYPE,
        'Accept-Encoding': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for Docspell v0.1',
    }
    try:
        url = f"{settings.APIURL['docspell']['url']}/open/auth/login"
        with requests.post(url, headers=headers, json=auth) as response:
            json_response = response.json()
            if 'token' in json_response and 'validMs' in json_response:
                return json_response['token']
            else:
                return None
    except:
        return None

def process(command, channel, username, params, files, conn):
    stripchars = r'\|\`\r\n\'\"'
    regex = re.compile('[%s]' % stripchars)
    if len(params)>0:
        try:
            messages = []
            querytypes = ('search', 'upload')
            if not params[0] in querytypes:
                querytype = 'search'
            else:
                querytype = params[0]
                params = params[1:]
            token = getToken()
            if token:
                headers = {
                    'Content-Type': settings.CONTENTTYPE,
                    'Accept-Encoding': settings.CONTENTTYPE,
                    'User-Agent': 'MatterBot integration for Docspell v0.1',
                    'X-Docspell-Auth': f"{token}",
                    'searchMode': 'Normal',
                    'query': 'string',
                }
                if querytype in ('search',):
                    reserved_str = r"""? & | ! { } [ ] ( ) ^ ~ * : \ " ' + -"""
                    esc_dict = { chr : f"\\{chr}" for chr in reserved_str}
                    res = [ ''.join(esc_dict.get(chr, chr) for chr in sub) for sub in params]
                    query = f'content%3A%22{' '.join(res)}%22'
                    url = f"{settings.APIURL['docspell']['url']}/sec/item/search?q={query}&withDetails=True"
                    with requests.get(url=url, headers=headers) as response:
                        json_response = response.json()
                        if "groups" in json_response:
                            if "name" in json_response['groups'][0]:
                                if json_response['groups'][0]['name'] == 'Results':
                                    items = json_response['groups'][0]['items']
                                    if len(items):
                                        files = []
                                        count = 0
                                        message = f"**Docspell Search Results for**: {' '.join(params)}\n\n"
                                        message += "| Date             | Name | Pages | Highlights |\n"
                                        message += "| ---------------- | :- | -: | :- |\n"
                                        for item in sorted(items, key=lambda items: items['date'], reverse=True):
                                            name = item['name']
                                            msdate = item['date']
                                            date = datetime.datetime.fromtimestamp(msdate/1000.0).strftime('%Y/%m/%d')
                                            attachments = item['attachments']
                                            if len(attachments):
                                                attachment = attachments[0]
                                                id = attachment['id']
                                                if 'pageCount' in attachment:
                                                    pages = attachment['pageCount']
                                                else:
                                                    pages = '-'
                                                if id:
                                                    url = f"{settings.APIURL['docspell']['url']}/sec/attachment/{id}"
                                                    headers = {
                                                        'Accept-Encoding': 'application/octet-stream',
                                                        'User-Agent': 'MatterBot integration for Docspell v0.1',
                                                        'X-Docspell-Auth': f"{token}",
                                                    }
                                                    with requests.get(url=url, headers=headers) as download:
                                                        entry = {'filename': name, 'bytes': download.content}
                                                        if not entry in files:
                                                            files.append(entry)
                                            else:
                                                attachments = '-'
                                            highlights = item['highlighting']
                                            if len(highlights):
                                                lines = []
                                                for highlight in highlights:
                                                    for line in highlight['lines']:
                                                        subline = regex.sub(' ', line)
                                                        keywords = regex.sub('',' '.join(params))
                                                        subline = re.findall(r'.{0,'+str(settings.PREAMBLE)+'}'+keywords+'.{0,'+str(settings.POSTAMBLE)+'}', subline, re.IGNORECASE)
                                                        if len(subline):
                                                            lines.append('... '+subline[0]+' ...')
                                                        else:
                                                            try:
                                                                subline = regex.sub(' ', line)
                                                                keywords = keywords.split(' AND ')[0]
                                                                keywords = keywords.split(' OR ')[0]
                                                                keywords = keywords.split(' && ')[0]
                                                                keywords = keywords.split(' || ')[0]
                                                                subline = re.findall(r'.{0,'+str(settings.PREAMBLE)+'}'+keywords+'.{0,'+str(settings.POSTAMBLE)+'}', subline, re.IGNORECASE)
                                                                if len(subline):
                                                                    lines.append('... '+subline[0]+' ...')
                                                                else:
                                                                    lines.append('*Search terms too far apart to show in highlight*')
                                                            except:
                                                                lines = ['*N/A*',]
                                            else:
                                                lines = ['*N/A*',]
                                            highlights = ' --- '.join(lines)
                                            message += f"| {date} | {name} | `{pages}` | {highlights} |\n"
                                            count += 1
                                            if count>9:
                                                message += '\n\n'
                                                message += f"*Returning the first **10** of **{len(items)}** results only; refine your search if needed!*\n"
                                                break
                                        if count>0:
                                            messages.append({'text': message})
                                            if len(files)>0:
                                                messages.append({'text': 'Related Downloads:', 'uploads': files})
                                        else:
                                            messages.append({'text': f"No results found for {params}"})
                if querytype in ('upload',):
                    if len(files):
                        print(files)
            else:
                messages.append({'text': "An error occurred acquiring a Docspell auth token. Check your settings and try again."})
        except Exception as e:
            messages.append({'text': "An error occurred accessing Docspell:`%s`\nError: %s" % (str(e),traceback.format_exc())})
        finally:
            return {'messages': messages}
