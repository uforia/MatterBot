#!/usr/bin/env python3

import collections
import graphviz
import itertools
import json
import os
import pprint
import re
import requests
import urllib
from pathlib import Path
try:
    from commands.attackmatrix import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    from commands.attackmatrix import defaults
    if Path('commands/attackmatrix/settings.py').is_file():
        try:
            from commands.attackmatrix import settings
        except ModuleNotFoundError: # local test run
            import defaults
            import settings

def process(command, channel, username, params, files, conn):
    messages = []
    querytypes = ('search', 'mitre', 'actoroverlap', 'ttpoverlap', 'findactor', 'matrices', 'config')
    querytype = params[0].strip()
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    categories = ('Actors', 'Techniques', 'Malwares', 'Tools', 'Mitigations', 'Tactics', 'Data Sources', 'Case Studies', 'Campaigns', 'Detection Rules', 'Code Snippets', 'Matrices')
    tableheaders = collections.OrderedDict({
        'type': 'Type',
        'name': 'Name',
        'details': 'MITRE ID',
    })
    if not params[0] in querytypes:
        messages.append({'text': 'Please specify an AttackMatrix query type: `'+'`, `'.join(querytypes)+'`.'})
    else:
        try:
            keywords = params[1:]
            if len(' '.join(keywords))<4 and not querytype in ('matrices', 'config'):
                messages.append({'text': 'Please specify at least one reasonably-sized keyword to query the AttackMatrix `'+querytype+'`.'})
            else:
                headers={
                    'Content-Type': settings.CONTENTTYPE,
                }
                if querytype in ('matrices', 'config'):
                    APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/explore/'
                    with requests.get(APIENDPOINT, headers=headers) as response:
                        json_response = response.json()
                        if len(json_response):
                            table = 'ATT&CK Matrix API endpoint currently has ' + str(len(json_response['Metadata']['matrices'])) + ' databases loaded:'
                            table += '\n\n'
                            table += '| **Matrix Name** | **Description** |\n'
                            table += '|:- |:- |\n'
                            for matrix in json_response['Metadata']['matrices']:
                                name = json_response['Metadata']['matrices'][matrix]['Metadata']['name'][0]
                                description = json_response['Metadata']['matrices'][matrix]['Metadata']['description'][0]
                                table += '| '+name+' | '+description+' |\n'
                            table += '\n\n'
                            messages.append({'text': table})
                if querytype == 'search':
                    searchterms = '&params='.join([urllib.parse.quote(_) for _ in keywords])
                    APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/search?params='+searchterms
                    with requests.get(APIENDPOINT, headers=headers) as response:
                        json_response = response.json()
                        if json_response != 'null':
                            if 'count' in json_response:
                                count = json_response['count']
                                if count==0:
                                    text = "No AttackMatrix API search results for: `%s`\n" % ('`, `'.join(keywords))
                                    messages.append({'text': text})
                                else:
                                    text = "AttackMatrix API search results for: `%s`\n" % ('`, `'.join(keywords))
                                    text += "\n"
                                    messages.append({'text': text})
                                    numresults = 0
                                    for category in categories:
                                        if category in json_response:
                                            table = '\n\n'
                                            table += '| **MITRE ID** | **'+category+'** | **Description** | **URL** |\n'
                                            table += '|:- |:- |:- |:- |\n'
                                            for entry in sorted(json_response[category]):
                                                jsonentry = json_response[category][entry]
                                                numresults += 1
                                                name = regex.sub(' ', ', '.join(jsonentry['Metadata']['name']))
                                                description = regex.sub(' ', ', '.join(jsonentry['Metadata']['description']))
                                                url = regex.sub(' ', ', '.join(jsonentry['Metadata']['url']))
                                                if len(description)>80:
                                                    description = description[:80]+' ...'
                                                table += '| '+entry+' | '+name+' | '+description+' | '+url+' |\n'
                                            table += '\n\n'
                                            messages.append({'text': table})
                if querytype == 'mitre':
                    mitreid = keywords[0].upper().strip()
                    for category in categories:
                        APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/explore/'+category+'/'+mitreid
                        with requests.get(APIENDPOINT, headers=headers) as response:
                            json_response = response.json()
                            result = False
                            if len(json_response)>0:
                                if 'error' in json_response:
                                    if json_response['error'].startswith('Key does not exist: '):
                                        continue
                                    messages.append({'text': 'An error occurred querying AttackMatrix:\nError: '+str(type(e))+': '+str(e)})
                                else:
                                    result = True
                                    table = '\n\n'
                                    table += '| **MITRE ID** | **Name** | **Description** | **URL** |\n'
                                    table += '|:- |:- |:- |:- |\n'
                                    name = regex.sub(' ', ' '.join(json_response['Metadata']['name']))
                                    description = regex.sub(' ', ' '.join(json_response['Metadata']['description']))
                                    url = regex.sub(' ', ' '.join(json_response['Metadata']['url']))
                                    table += '| '+mitreid+' | '+name+' | '+description+' | '+url+' |\n'
                                    table += '\n\n'
                                    messages.append({'text': table})
                                    for category in categories:
                                        if category in json_response:
                                            if len(json_response[category]):
                                                table = '\n\n**Associated** `'+category+'`\n'
                                                table += '\n\n'
                                                table += '| **MITRE ID** | **Name ** | **URL** |\n'
                                                table += '|:- |:- |:- |\n'
                                                for entry in sorted(json_response[category]):
                                                    name = regex.sub(' ', ' '.join(json_response[category][entry]['name']))
                                                    url = regex.sub(' ', ' '.join(json_response[category][entry]['url']))
                                                    table += '| '+entry+' | '+name+' | '+url+' |\n'
                                                table += '\n\n'
                                                messages.append({'text': table})
                                    break
                        if not result:
                            messages.append({'text': 'AttackMatrix: MITRE ID not found.'})
                if querytype == 'actoroverlap':
                    keywords = [_.upper().strip() for _ in keywords]
                    searchterms = '&actors='.join([urllib.parse.quote(_) for _ in keywords])
                    if re.search(r"[\w\s,.\+\-]+", searchterms):
                        text = None
                        APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/actoroverlap?actors='+searchterms
                        with requests.get(APIENDPOINT, headers=headers) as response:
                            json_response = response.json()
                            if len(json_response)>0:
                                if 'error' in json_response:
                                    text = 'AttackMatrix error: '+json_response['error']
                                else:
                                    count = json_response.pop('count')
                                    actorttps = {}
                                    commonttps = {}
                                    for actor in json_response:
                                        for category in categories:
                                            if category in json_response[actor]:
                                                commonttps[category] = {}
                                                for entry in json_response[actor][category]:
                                                    commonttps[category][entry] = json_response[actor][category][entry]
                                        table = '**Common TTPs** for '
                                        for actor in keywords:
                                            table += '`'+actor+'`: `'
                                            table += '`, `'.join(json_response[actor]['Metadata']['name'])
                                            table += '` and '
                                        table = table[:-5]
                                        table += '\n\n\n'
                                        table += '| **Type** | **MITRE ID** | **Name** |\n'
                                        table += '|:- |:- |:- |\n'
                                        for category in commonttps:
                                            for entry in sorted(commonttps[category]):
                                                name = regex.sub(' ', ' '.join(commonttps[category][entry]['name']))
                                                table += '| '+category+' | '+entry+' | '+name+' |\n'
                                        table += '\n\n'
                                        messages.append({'text': table})
                                        break
                                    for actor in keywords:
                                        actorttps[actor] = {}
                                        APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/explore/Actors/'+actor
                                        with requests.get(APIENDPOINT, headers=headers) as response:
                                            json_response = response.json()
                                            for commonttpcategory in commonttps:
                                                if commonttpcategory in commonttps:
                                                    if len(json_response[commonttpcategory]) == 0:
                                                        del json_response[commonttpcategory]
                                                        continue
                                                for commonttp in commonttps[commonttpcategory]:
                                                    del json_response[commonttpcategory][commonttp]
                                        actorttps[actor] = json_response
                                for actor in keywords:
                                    table = '\n\n'
                                    table += '**Unique TTPs** for `'+actor+'`: `'
                                    table += '`, `'.join(actorttps[actor]['Metadata']['name'])
                                    table += '`\n\n\n'
                                    messages.append({'text': table})
                                    for category in actorttps[actor]:
                                        if len(actorttps[actor][category])>0:
                                            table = '\n\n'
                                            if category in categories:
                                                table += '| **Type** | **MITRE IDs** |\n'
                                                table += '|:- |:- |\n'
                                                table += '| '+category+' | '
                                                for entry in sorted(actorttps[actor][category]):
                                                    name = regex.sub(' ', ' '.join(actorttps[actor][category][entry]['name']))
                                                    table += entry+': '+name+', '
                                                table = table[:-2]
                                                table += '|\n'
                                                table += '\n\n'
                                            messages.append({'text': table})
                                # Create a graph
                                filename = 'Actor-overlap-for-'+'-'.join(keywords)+'.png'
                                graph = graphviz.Digraph(comment=filename, format='png')
                                graph.attr(layout='sfdp', overlap='prism')
                                # Create the actor nodes
                                for actorid in actorttps:
                                    contents = actorid+'\n'
                                    contents += ', '.join(actorttps[actorid]['Metadata']['name'])
                                    # Add all actors to the graph
                                    graph.node(actorid,
                                               contents,
                                               style='filled',
                                               fillcolor='#000080',
                                               fontcolor='white')
                                    # Add all TTPs to the graph
                                    for category in categories:
                                        if category in actorttps[actorid]:
                                            for ttpid in actorttps[actorid][category]:
                                                entry = actorttps[actorid][category][ttpid]
                                                contents = ttpid+'\n'
                                                contents += ', '.join(entry['name'])
                                                graph.node(ttpid,
                                                           contents,
                                                           shape='box',
                                                           style='filled',
                                                           fillcolor='#800000',
                                                           fontcolor='white')
                                                graph.edge(actorid, ttpid)
                                # Create the nodes for the TTPs they have in common
                                for category in categories:
                                    if category in commonttps:
                                        for ttpid in commonttps[category]:
                                            entry = commonttps[category][ttpid]
                                            contents = ttpid+'\n'
                                            contents += ', '.join(entry['name'])
                                            graph.node(ttpid,
                                                       contents,
                                                       shape='box',
                                                       style='filled',
                                                       fillcolor='#008000',
                                                       fontcolor='white')
                                            for actor in keywords:
                                                graph.edge(actor, ttpid)
                                bytes = graph.pipe()
                                messages.append({
                                    'text': 'Graphical representation of overlap:\n', 'uploads': [{'filename': filename, 'bytes': bytes}]
                                })
                            else:
                                messages.append({'text': 'AttackMatrix: invalid MITRE Actor ID or no overlap.\n'})
                if querytype == 'ttpoverlap':
                    keywords = [_.upper().strip() for _ in keywords]
                    searchterms = '&ttps='.join([urllib.parse.quote(_) for _ in keywords])
                    if re.search(r"[\w\s,.\+\-]+", searchterms):
                        text = None
                        APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/ttpoverlap?ttps='+searchterms
                        with requests.get(APIENDPOINT, headers=headers) as response:
                            json_response = response.json()
                            if len(json_response)>0:
                                count = len(json_response)
                                if 'error' in json_response:
                                    text = 'AttackMatrix error: '+json_response['error']
                                else:
                                    if count>settings.MAXRESULTS:
                                        text = 'AttackMatrix: More than '+str(settings.MAXRESULTS)+' actors match your TTP set, '
                                        text += 'making the resulting data set too large to be useful. Narrow down your selection by '
                                        text += 'either adding more TTPs or selecting more specific TTPs.\n'
                                        text += 'You are currently matching '+str(count)+' actors: `'+'`, `'.join(sorted(json_response.keys()))+'`.'
                                        messages.append({'text': text})
                                    else:
                                        actors = sorted(list(json_response.keys()))
                                        additionalttps = {}
                                        commonttps = []
                                        table = '**Common TTPs** for '
                                        for actor in json_response.keys():
                                            table += '`'+actor+'`: `'
                                            table += '`, `'.join(json_response[actor]['Metadata']['name'])
                                            table += '` and '
                                        table = table[:-5]
                                        table += '\n\n\n'
                                        table += '| **Type** | **MITRE ID** | **Name** |\n'
                                        table += '|:- |:- |:- |\n'
                                        allttps = {}
                                        for actor in actors:
                                            for category in categories:
                                                if category == 'Actors':
                                                    continue
                                                if category in json_response[actor]:
                                                    if category not in allttps:
                                                        allttps[category] = {}
                                                    for ttp in json_response[actor][category]:
                                                        if ttp not in allttps[category]:
                                                            allttps[category][ttp] = json_response[actor][category][ttp]
                                        commonttps = {}
                                        for ttpcategory in allttps:
                                            commonttps[ttpcategory] = {}
                                            for ttp in allttps[ttpcategory]:
                                                # First, assume the TTP exists for all actors
                                                exists = True
                                                for actor in actors:
                                                    if ttpcategory in json_response[actor]:
                                                        if not ttp in json_response[actor][ttpcategory]:
                                                            # Check if the TTP exists for every actor, otherwise set to False
                                                            exists = False
                                                if exists:
                                                    commonttps[ttpcategory][ttp] = json_response[actor][ttpcategory][ttp]
                                            if len(commonttps[ttpcategory])==0:
                                                del commonttps[ttpcategory]
                                        for category in commonttps:
                                            for ttp in sorted(commonttps[category]):
                                                table += '| '+category+' '
                                                table += '| '+ttp+' '
                                                name = regex.sub(' ', ' '.join(commonttps[category][ttp]['name']))
                                                table += '| '+name+' '
                                                table += '|\n'
                                        table += '\n\n'
                                        messages.append({'text': table})
                                        for actor in actors:
                                            numresults = 0
                                            table = '**Unique TTPs** for '
                                            table += '`'+actor+'`: `'
                                            table += '`, `'.join(json_response[actor]['Metadata']['name'])
                                            table += '`'
                                            table += '\n\n\n'
                                            table += '| **Type** | **MITRE ID** | **Name** |\n'
                                            table += '|:- |:- |:- |\n'
                                            for category in categories:
                                                if category == 'Actors':
                                                    continue
                                                if category in json_response[actor]:
                                                    for ttp in sorted(json_response[actor][category]):
                                                        if category in commonttps:
                                                            if not ttp in commonttps[category]:
                                                                table += '| '+category+' '
                                                                table += '| '+ttp+' '
                                                                name = regex.sub(' ', ' '.join(json_response[actor][category][ttp]['name']))
                                                                table += '| '+name+' '
                                                                table += '|\n'
                                                                numresults += 1
                                            table += '\n\n'
                                            if numresults>0:
                                                messages.append({'text': table})
                                        # Digraph
                                        filename = 'TTP-overlap-for-'+'-'.join(actors)+'.png'
                                        graph = graphviz.Digraph(comment=filename, format='png')
                                        graph.attr(layout='sfdp', overlap='prism')
                                        # Create the actor nodes
                                        for actor in actors:
                                            contents = actor+'\n'
                                            contents += ' '.join(json_response[actor]['Metadata']['name'])
                                            graph.node(actor,
                                                       contents,
                                                       style='filled',
                                                       fillcolor='#000080',
                                                       fontcolor='white')
                                            for category in categories:
                                                if category == 'Actors':
                                                    continue
                                                if category in json_response[actor]:
                                                    for ttp in json_response[actor][category]:
                                                        if category in commonttps:
                                                            if not ttp in commonttps[category]:
                                                                mitreid = ttp
                                                                contents = mitreid+'\n'
                                                                contents += ' '.join(json_response[actor][category][ttp]['name'])
                                                                graph.node(mitreid,
                                                                           contents,
                                                                           shape='box',
                                                                           style='filled',
                                                                           fillcolor='#800000',
                                                                           fontcolor='white')
                                                                graph.edge(actor, mitreid)
                                        # Create the nodes for the TTPs they have in common
                                        for category in commonttps:
                                            if category in categories:
                                                if category in commonttps:
                                                    for ttp in commonttps[category]:
                                                        mitreid = ttp
                                                        contents = mitreid+'\n'
                                                        contents += ' '.join(commonttps[category][ttp]['name'])
                                                        graph.node(mitreid,
                                                                   contents,
                                                                   shape='box',
                                                                   style='filled',
                                                                   fillcolor='#008000',
                                                                   fontcolor='white')
                                                        for actor in actors:
                                                            graph.edge(actor, mitreid)
                                        bytes = graph.pipe()
                                        messages.append({
                                            'text': 'Graphical representation of overlap:\n', 'uploads': [{'filename': filename, 'bytes': bytes}]
                                        })
                            else:
                                if len(keywords)>1:
                                    messages.append({
                                        'text': 'AttackMatrix: no results found for `'+'`, `'.join(keywords)+'`.'
                                    })
                                else:
                                    messages.append({
                                        'text': 'AttackMatrix: you must specify at least two TTPs!'
                                    })
                if querytype == 'findactor':
                    keywords = [_.upper().strip() for _ in keywords]
                    searchterms = '&ttps='.join([urllib.parse.quote(_) for _ in keywords])
                    if len(keywords)>2:
                        if re.search(r"[\w\s,.\+\-]+", searchterms):
                            APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/findactor?ttps='+searchterms
                            with requests.get(APIENDPOINT, headers=headers) as response:
                                json_response = response.json()
                                if len(json_response)>0:
                                    count = json_response['count']
                                    if 'error' in json_response:
                                        text = 'AttackMatrix error: '+json_response['error']
                                        messages.append({'text': text})
                                    else:
                                        table = 'Found ' + str(count) + ' potential matches:\n\n'
                                        table += '| **MITRE ID** | **Name** | **Matching TTPs** | **TTP Match %** | **TTP Known %** |\n'
                                        table += '| :-           | :-       | :-                |              -: |              -: |\n'
                                        for actor in json_response:
                                            if actor != 'count':
                                                id = json_response[actor]['id']
                                                name = json_response[actor]['name']
                                                matching_ttps = json_response[actor]['matching_ttps']
                                                num_matching_ttps = str(json_response[actor]['num_matching_ttps'])
                                                num_given_ttps = str(json_response[actor]['num_given_ttps'])
                                                num_known_ttps = str(json_response[actor]['num_known_ttps'])
                                                matching_coverage = json_response[actor]['matching_coverage']
                                                total_coverage = json_response[actor]['total_coverage']
                                                table += '| ' + id
                                                table += ' | ' + name
                                                table += ' | ' + ', '.join(matching_ttps)
                                                table += ' | ' + num_matching_ttps + '/' + num_given_ttps + ' (' + matching_coverage + ')'
                                                table += ' | ' + num_matching_ttps + '/' + num_known_ttps + ' (' + total_coverage + ')'
                                                table += ' |\n'
                                        table += '\n\n'
                                        messages.append({'text': table})
        except Exception as e:
            messages.append({'text': 'An error occurred querying AttackMatrix:\nError: '+str(type(e))+': '+str(e)})
        finally:
            return {'messages': messages}
