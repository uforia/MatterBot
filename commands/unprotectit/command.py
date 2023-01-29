#!/usr/bin/env python3

import json
import os
import re
import requests
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

def process(command, channel, username, params):
    if len(params):
        stripchars = ' `\n\r\'\"'
        regex = re.compile('[%s]' % stripchars)
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        if params[0] == 'rebuildcache':
            if os.path.isfile(settings.CACHE):
                page = 1
                techniques = {'techniques': []}
                with requests.get(settings.APIURL['unprotectit']['url'], headers=headers) as response:
                    json_response = response.json()
                    if 'count' in json_response:
                        if 'results' in json_response:
                            results = json_response['results']
                            for result in results:
                                techniques['techniques'].append(result)
                        # Grab the next pages as well (if they exist)
                        if 'next' in json_response:
                            nextpage = json_response['next']
                            while nextpage:
                                print(nextpage)
                                with requests.get(nextpage, headers=headers) as response:
                                    json_response = response.json()
                                    if 'count' in json_response:
                                        if 'results' in json_response:
                                            results = json_response['results']
                                            for result in results:
                                                techniques['techniques'].append(result)
                                            if 'next' in json_response:
                                                nextpage = json_response['next']
                if len(techniques):
                    with open(settings.CACHE, mode='w') as f:
                        cache = json.dumps(techniques)
                        f.write(cache)
                        text = "Unprotect.it cache rebuilt."
                        return {'messages': [
                            {'text': text},
                        ]}
        try:
            messages = []
            uploads = []
            techniques = {'techniques': []}
            # Check if the local cache already exists. If so, skip the cache building
            # perform the search query. Otherwise, build the cache first and then do
            # the search.
            if os.path.isfile(settings.CACHE):
                with open(settings.CACHE, mode='r') as f:
                    cache = f.read()
                    techniques = json.loads(cache)
                    source = 'cache'
            else:
                page = 1
                with requests.get(settings.APIURL['unprotectit']['url'], headers=headers) as response:
                    json_response = response.json()
                    if 'count' in json_response:
                        if 'results' in json_response:
                            results = json_response['results']
                            for result in results:
                                techniques['techniques'].append(result)
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
                                                techniques['techniques'].append(result)
                                            if 'next' in json_response:
                                                nextpage = json_response['next']
                        source = 'website'
                if len(techniques):
                    with open(settings.CACHE, mode='w') as f:
                        cache = json.dumps(techniques)
                        f.write(cache)
            text = 'Unprotect.it results for `' + '`, `'.join(params) + '`:\n'
            text += '*(Loaded ' + str(len(techniques['techniques'])) + ' techniques from ' + source + ')*'
            messages.append({'text': text})
            # Check if all search terms appear in the content (logical AND search)
            results = 0
            for technique in techniques['techniques']:
                name = technique['name']
                ids = set()
                unprotect_ids = technique['unprotect_id'].split(',')
                for unprotect_id in unprotect_ids:
                    ids.add(regex.sub('', unprotect_id))
                categories = set()
                for category in technique['categories']:
                    categories.add(category['label'])
                description = technique['description']
                resources = []
                for resource in technique['resources'].split('\n'):
                    resources.append(regex.sub('', resource))
                tags = set()
                for tag in technique['tags'].split(','):
                    tags.add(regex.sub('', tag))
                snippets = []
                for snippet in technique['snippets']:
                    snippet_description = snippet['description']
                    snippet_plain_code = snippet['plain_code']
                    codesnippet = '\n**Code Snippet**: `' + snippet_description + '`\n'
                    snippet_code_class = regex.sub('', snippet['language']['code_class'])
                    if not snippet_code_class in defaults.LANGS:
                        snippet_code_class = ''
                    snippets.append(
                        codesnippet +
                        '\n  ```' + snippet_code_class + '\n' +
                        snippet_plain_code + '\n```'
                    )
                detection_rules = []
                rules = []
                for detection_rule in technique['detection_rules']:
                    detection_rule_syntax_lang = detection_rule['type']['syntax_lang'].lower()
                    detection_rule_name = detection_rule['name'].lower()
                    detection_rule_rule = detection_rule['rule']
                    detection_rules.append(detection_rule_name + '\n' + detection_rule_rule + '\n')
                    rules.append({
                        'name': detection_rule_name + '.' + detection_rule_syntax_lang,
                        'rule': detection_rule_rule.encode(),
                    })
                if any([
                    all(param in name for param in params),
                    all(param in unprotect_id for param in params),
                    all(param in ' '.join(categories) for param in params),
                    all(param in description for param in params),
                    all(param in ' '.join(resources) for param in params),
                    all(param in ' '.join(tags) for param in params),
                    all(param in ' '.join(snippets) for param in params),
                    all(param in ' '.join(detection_rules) for param in params),
                    ]):
                    results += 1
                    text = '\n\n---\n'
                    text += '\n**Technique**: `' + name + '` '
                    techniquetype = None
                    if len(ids):
                        text += '**IDs**: '
                        for id in ids:
                            text += '[' + id + ']('
                            if id.startswith('T'):
                                techniquetype = 'Techniques'
                                if '.' in id:
                                    techniquetype = 'Subtechniques'
                                text += settings.APIURL['attackmatrix']['url']
                                text += '&cat=' + techniquetype
                                text += '&id=' + id
                            else:
                                text += 'https://unprotect.it/search/?keyword=' + id
                            text += '), '
                        text = text[:-2]
                    text += '\n**Categories**: '
                    text += '`' + '`, `'.join(categories) + '`'
                    text += ' **References**: '
                    for resource in resources:
                        text += '[' + str(resources.index(resource)+1) + ']'
                        text += '(' + resource + '), '
                    text = text[:-2]
                    messages.append({'text': text})
                    for snippet in snippets:
                        messages.append({'text': snippet})
                    for rule in rules:
                        name = rule['name']
                        rule = rule['rule']
                        uploads.append({'filename': name, 'bytes': rule})
                    if len(uploads):
                        detection = '\n\n---\n\n**Detection Rules**:'
                        messages.append({'text': detection, 'uploads': uploads})
            if not len(messages):
                text = 'Unprotect.it search for `' + '`, `'.join(params) + '`: no results found'
                messages.append({'text': text})
        except Exception as e:
            messages.append({'text': 'An error occurred searching Unprotect.it:\nError: ' + str(e)})
        finally:
            return {'messages': messages}
