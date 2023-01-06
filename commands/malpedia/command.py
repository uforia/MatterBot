#!/usr/bin/env python3

import base64
import httpx
import json
import re
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

async def process(connection, channel, username, params):
    if len(params)>0:
        params = params[0]
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'Authorization': 'apitoken %s' % (settings.APIURL['malpedia']['key'],),
        }
        text = "Malpedia search for `%s`: " % (params,)
        try:
            hash_algo = None
            bytes = None
            filename = None
            result = {'messages': []}
            if re.search(r"^[A-Za-z0-9]{32}$", params):
                hash_algo = 'md5'
            elif re.search(r"^[A-Za-z0-9]{64}$", params):
                hash_algo = 'sha256'
            if hash_algo:
                apipath = 'get/sample/%s/zip' % (params,)
                async with httpx.AsyncClient(headers=headers) as session:
                    response = await session.get(settings.APIURL['malpedia']['url'] + apipath)
                    json_response = response.json()
                    if 'detail' in json_response:
                        # You don't have a registered account/API key to get samples!
                        if json_response['detail'] == 'Authentication credentials were not provided.':
                            return ("An error occured searching Malpedia: you need a registered account/API key to search for hashes!",)
                    elif 'zipped' in json_response:
                        # We found a sample!
                        filename = params
                        bytes = base64.b64decode(json_response['zipped'].encode())
                    else:
                        text += 'returned no results.'
                    if filename and bytes:
                        result['messages'].append(
                            {'text': text, 'uploads': [{'filename': filename, 'bytes': bytes}]}
                        )
                    else:
                        result['messages'].append(
                            {'text': text}
                        )
                return result
            else:
                apipath = 'find/actor/%s' % (params,)
                async with httpx.AsyncClient(headers=headers) as session:
                    response = await session.get(settings.APIURL['malpedia']['url'] + apipath)
                    actors = response.json()
                apipath = 'find/family/%s' % (params,)
                async with httpx.AsyncClient(headers=headers) as session:
                    response = await session.get(settings.APIURL['malpedia']['url'] + apipath)
                    families = response.json()
                if actors:
                    for actor in actors:
                        actornames = []
                        actornames.append(actor['common_name'])
                        actornames.extend(actor['synonyms'])
                        # Now find the common tools this actor uses
                        text += '\n- Actor names/synonyms: `' + '`, `'.join(sorted(actornames)) + '`'
                        for actorname in actornames:
                            if re.search(r"^G[0-9]{4}$", actorname):
                                async with httpx.AsyncClient(headers=headers) as session:
                                    response = await session.get(settings.APIURL['mitre']['url'] + 'Enterprise/Actors/' + actorname)
                                    mitre = response.json()
                                    if mitre:
                                        mitre = mitre['Enterprise']['Actors'][actorname]
                                        for subtree in 'Malwares', 'Subtechniques', 'Techniques':
                                            if subtree in mitre:
                                                items = set()
                                                for mitrecode in mitre[subtree]:
                                                    name = mitre[subtree][mitrecode]['name']
                                                    entry = '`' + mitrecode + '` '
                                                    entry += '[' + settings.APIURL['mitre']['url'] + 'Enterprise/' + subtree + '/' + mitrecode + ']'
                                                    entry += '(' + name + ')'
                                                    items.add(entry)
                                                text += '\n  - `' + subtree + '`: '
                                                text += ', '.join(sorted(items))
                        result['messages'].append(
                            {'text': text},
                        )
                if families:
                    for family in families:
                        familynames = []
                        familynames.append(family['name'])
                        familynames.extend(family['alt_names'])
                        # Now find the common tools this actor uses
                        text += '\n- Malware names/synonyms: `' + '`, `'.join(sorted(familynames)) + '`'
                        result['messages'].append(
                            {'text': text},
                    )
                print(result)
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred searching Malpedia for `%s`:\nError: `%s`' % (params, e.message)},
            ]}
