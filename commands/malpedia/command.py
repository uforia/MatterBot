#!/usr/bin/env python3

import base64
import json
import re
import requests
from pathlib import Path
try:
    from commands.malpedia import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/malpedia/settings.py').is_file():
        try:
            from commands.malpedia import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        params = params[0].replace('[.]','.')
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'Authorization': 'apitoken %s' % (settings.APIURL['malpedia']['key'],),
        }
        try:
            hash_algo = None
            bytes = None
            filename = None
            messages = []
            if re.search(r"^[A-Fa-f0-9]{32}$", params):
                hash_algo = 'md5'
            elif re.search(r"^[A-Fa-f0-9]{64}$", params):
                hash_algo = 'sha256'
            if hash_algo:
                apipath = 'get/sample/%s/zip' % (params,)
                uploads = None
                with requests.get(settings.APIURL['malpedia']['url'] + apipath, headers=headers) as response:
                    json_response = response.json()
                    if 'detail' in json_response:
                        # You don't have a registered account/API key to get samples!
                        detail = json_response['detail']
                        text = 'Malpedia hash search for `%s`: %s' % (params, detail)
                    elif 'zipped' in json_response:
                        # We found a sample!
                        filename = params
                        bytes = base64.b64decode(json_response['zipped'].encode())
                        text = 'Malpedia hash search for `%s`:\n' % (params,)
                        if filename and bytes:
                            uploads = [{'filename': filename, 'bytes': bytes}]
                messages.append({'text': text, 'uploads': uploads})
            if re.search(r"^[A-Za-z0-9]+$", params):
                apipath = 'find/actor/%s' % (params,)
                with requests.get(settings.APIURL['malpedia']['url'] + apipath, headers=headers) as response:
                    actors = response.json()
                apipath = 'find/family/%s' % (params,)
                with requests.get(settings.APIURL['malpedia']['url'] + apipath, headers=headers) as response:
                    families = response.json()
                if actors:
                    items = {}
                    subtrees = ('Malwares', 'Matrices', 'Mitigations', 'Techniques', 'Tools')
                    for subtree in subtrees:
                        items[subtree] = set()
                    text = 'Malpedia actor search for `%s`:' % (params,)
                    for actor in actors:
                        actornames = []
                        actornames.append(actor['common_name'])
                        actornames.extend(actor['synonyms'])
                        # Now find the common tools this actor uses
                        text += '\n**Actor names/synonyms**: `' + '`, `'.join(sorted(actornames, key=str.lower)) + '`'
                        for actorname in actornames:
                            if re.search(r"^G[0-9]{4}$", actorname):
                                with requests.get(settings.APIURL['mitre']['url'] + 'Actors/' + actorname, headers=headers) as response:
                                    mitre = response.json()
                                    if mitre:
                                        for subtree in subtrees:
                                            if not subtree in items:
                                                if len(mitre[subtree])>0:
                                                    items[subtree] = list()
                                            if subtree in mitre:
                                                if len(mitre[subtree])>0:
                                                    for mitrecode in sorted(mitre[subtree], key=str.lower):
                                                        name = ' '.join(mitre[subtree][mitrecode]['name'])
                                                        mitreid = mitrecode
                                                        items[subtree].add((mitreid, name))
                    text += '\n'
                    messages.append({'text': text})
                    for subtree in subtrees:
                        if len(items[subtree])>0:
                            text = '**Associated** `'+subtree+'` **TTPs for** `%s`:' % (params,)
                            text += '\n\n'
                            text += '| Name(s) |\n'
                            text += '|:- |\n'
                            text += '| '
                            for mitreid, name in sorted(items[subtree]):
                                text += '**'+mitreid+'**: '+name+', '
                            text = text[:-2]
                            text += ' |\n'
                            text += '\n\n'
                        messages.append({'text': text})
                if families:
                    text = 'Malpedia malware search for `%s`:' % (params,)
                    for family in families:
                        malwarenames = []
                        malwarenames.append(family['name'])
                        malwarenames.extend(family['alt_names'])
                        entry = '`, `'.join(sorted(malwarenames, key=str.lower))
                        text += '\n**Malware family**: `' + entry + '`'
                    messages.append({'text': text})
        except Exception as e:
            messages.append({'text': 'An error occurred searching Malpedia for `%s`:\nError: `%s`: `%s`' % (params, str(type(e)), str(e))},)
        finally:
            return {'messages': messages}
