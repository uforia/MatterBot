#!/usr/bin/env python3

import json
import os
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.unprotectit import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    from commands.unprotectit import defaults
    if Path('commands/unprotectit/settings.py').is_file():
        try:
            from commands.unprotectit import settings
        except ModuleNotFoundError: # local test run
            import defaults
            import settings

def buildcache(messages):
    try:
        cache = {}
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        page = 1
        with requests.get(settings.APIURL['unprotectit']['url'], headers=headers) as cat_response:
            cat_json_response = cat_response.json()
            for category in cat_json_response:
                cache[category] = {}
                with requests.get(cat_json_response[category], headers=headers) as response:
                    json_response = response.json()
                    if 'count' in json_response:
                        if 'results' in json_response:
                            results = json_response['results']
                            for result in results:
                                if 'id' in result:
                                    id = result['id']
                                    cache[category][result['id']] = result
                        # Grab the next pages as well (if they exist)
                        if 'next' in json_response:
                            nextpage = json_response['next']
                            while nextpage:
                                with requests.get(nextpage, headers=headers) as response:
                                    json_response = response.json()
                                    if 'count' in json_response:
                                        if 'results' in json_response:
                                            results = json_response['results']
                                            for result in results:
                                                if 'id' in result:
                                                    id = result['id']
                                                    cache[category][id] = result
                                            if 'next' in json_response:
                                                nextpage = json_response['next']
                if not len(cache[category]):
                    del cache[category]
        if len(cache):
            with open(settings.CACHE, mode='w') as f:
                fh = json.dumps(cache)
                f.write(fh)
                message = "**Unprotect.it Cache Rebuilt**:\n\n"
                message += '| Category | Entries |\n'
                message += '| :- | -: |\n'
                for category in sorted(cache.keys()):
                    message += '| '+category.replace('_',' ').title()+' | '+str(len(cache[category]))+' |\n'
                message += '\n'
                return message
    except Exception as e:
        return 'An error occurred during the Unprotect.it cache building:\nError:\n'+traceback.format_exc()

def process(command, channel, username, params, files, conn):
    if len(params):
        messages = []
        stripchars = ' `\n\r\'\"'
        regex = re.compile('[%s]' % stripchars)
        if not os.path.isfile(settings.CACHE) or params[0] == 'rebuildcache':
            messages.append({'text': buildcache(messages)})
        with open(settings.CACHE, mode='r') as f:
            data = f.read()
            cache = json.loads(data)
        try:
            # Check if the local cache already exists. If so, skip the cache building
            # perform the search query. Otherwise, build the cache first and then do
            # the search.
            # Check if all search terms appear in the content (logical AND search)
            results = 0
            searchmap = {
                'techniques': [
                    'unprotect_id',
                    'name',
                    'description',
                    'tags',
                ],
                'detection_rules': [
                    'name',
                    'rule',
                ],
                'snippets': [
                    'plain_code',
                    'description',
                ],
                'windows_library': [
                    'name',
                    'description',
                ],
            }
            urlmap = {
                'techniques': 'technique',
                'detection_rules': 'detection_rule',
            }
            results = []
            uploads = []
            for category in cache:
                if category in searchmap:
                    for searchfield in searchmap[category]:
                        for entry in cache[category]:
                            if any(param.lower() in cache[category][entry][searchfield].lower() for param in params):
                                resultcategory = category.replace('_',' ').title()
                                if category in ('techniques','windows_library'):
                                    value = cache[category][entry]['description']
                                    if category in urlmap:
                                        link = settings.APIURL['unprotectit']['url'].replace('/api','')+'/'+urlmap[category]+'/'+cache[category][entry]['key']
                                        url = f'[{entry}]({link})'
                                    else:
                                        url = 'N/A'
                                    results.append((resultcategory,value,url))
                                if category in ('detection_rules'):
                                    bytes = cache[category][entry]['rule'].encode()
                                    name = cache[category][entry]['name'].lower()+'_'+entry.lower()
                                    dettext = cache[category][entry]['type']['name'].lower()
                                    dettype = cache[category][entry]['type']['syntax_lang'].lower()
                                    uploads.append({'filename': 'unprotectit-'+name+'-'+dettext+'.'+dettype, 'bytes': bytes})
                                if category in ('snippets'):
                                    bytes = cache[category][entry]['plain_code'].encode()
                                    name = resultcategory.lower()+'_'+entry.lower()
                                    langtext = cache[category][entry]['language']['label'].lower()
                                    langtype = cache[category][entry]['language']['code_class'].lower()
                                    uploads.append({'filename': 'unprotectit-'+name+'-'+langtext+'.'+langtype, 'bytes': bytes})
            if len(results):
                message = 'Unprotect.it results for `' + '`, `'.join(params) + '`:\n\n'
                message += '| Category | Value | UPI ID |\n'
                message += '| :- | :- | :- |\n'
                for result in results:
                    category,value,url = result
                    category = regex.sub(' ',category)
                    value = regex.sub(' ',value)
                    if len(value)>400:
                        value = value.split('. ')[0]+'...'
                    message += f'| {category} | {value} | {url} |\n' 
                message += '\n'
                messages.append({'text': message})
            if len(uploads):
                chunks = [uploads[_:_ + 10] for _ in range(0, len(uploads), 10)]
                for chunk in chunks:
                    messages.append({'text': 'Related Downloads', 'uploads': chunk})
        except Exception as e:
            messages.append({'text': 'An error occurred in the Unprotect.it module:\nError: '+traceback.format_exc()})
        finally:
            return {'messages': messages}
