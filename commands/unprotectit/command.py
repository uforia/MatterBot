#!/usr/bin/env python3

import collections
import json
import os
import re
import requests
import traceback

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
            }
            urlmap = {
                'techniques': {
                    'link': 'technique',
                    'name': 'unprotect_id',
                },
                'detection_rules': 'detection_rule',
            }
            results = []
            fieldorder = collections.OrderedDict({
                'Unprotect ID(s)': 'url',
                'Value': 'value',
            })
            uploads = []
            for category in cache:
                if category in searchmap:
                    for searchfield in searchmap[category]:
                        for entry in cache[category]:
                            if all(param.lower() in cache[category][entry][searchfield].lower() for param in params):
                                resultcategory = category.replace('_',' ').title()
                                if category in ('techniques',):
                                    value = cache[category][entry]['description']
                                    if category in urlmap:
                                        linkval = urlmap[category]['link']
                                        nameval = urlmap[category]['name']
                                        keyval = cache[category][entry]['key']
                                        link = settings.APIURL['unprotectit']['url'].replace('/api','')+'/'+linkval+'/'+keyval
                                        url = f'[{cache[category][entry][nameval]}]({link})'
                                    else:
                                        url = 'N/A'
                                    results.append({
                                        'category': resultcategory,
                                        'value': value,
                                        'url': url,
                                    })
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
                for field in fieldorder:
                    message += f'| {field} '
                message += '|\n'
                message += len(fieldorder.keys())*'| :- '
                message += '|\n'
                for result in results:
                    for field in fieldorder:
                        fieldvalue = fieldorder[field]
                        value = regex.sub(' ',result[fieldvalue])
                        if len(value)>400:
                            value = value.split('. ')[0]+'...'
                        message += f'| {value} ' 
                    message += '|\n'
                message += '\n'
                messages.append({'text': message})
            if len(uploads):
                chunks = [uploads[_:_ + 10] for _ in range(0, len(uploads), 10)]
                for chunk in chunks:
                    messages.append({'text': f'Unprotect.it Related Downloads for `%s`' % ('`, `'.join(params)), 'uploads': chunk})
        except Exception as e:
            messages.append({'text': 'An error occurred in the Unprotect.it module:\nError: '+traceback.format_exc()})
        finally:
            return {'messages': messages}
