#!/usr/bin/env python3

import collections
import graphviz
import httpx
import json
import os
import re
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

async def process(command, channel, username, params):
    messages = []
    querytypes = ('search', 'mitre', 'actoroverlap', 'ttpoverlap')
    querytype = params[0].strip()
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    matrices = ('Enterprise', 'ICS', 'Mobile', 'PRE')
    categories = ('Actors', 'Malwares', 'Mitigations', 'Subtechniques', 'Tactics', 'Techniques', 'Tools')
    tableheaders = collections.OrderedDict({
        'type': 'Type',
        'name': 'Name',
        'details': 'MITRE ID',
    })
    if not params[0] in querytypes:
        messages.append({'text': 'Please specify an AttackMatrix query type: `' + '`, `'.join(querytypes) + '`.'})
    else:
        try:
            keywords = params[1:]
            if len(' '.join(keywords))<4:
                messages.append({'text': 'Please specify at least one reasonably-sized keyword to query the AttackMatrix `' + querytype + '`.'})
            else:
                headers={
                    'Content-Type': settings.CONTENTTYPE,
                }
                if querytype == 'search':
                    searchterms = '&params='.join([urllib.parse.quote(_) for _ in keywords])
                    if re.search(r"[\w\s,.\+\-]+", searchterms):
                        APIENDPOINT = settings.APIURL['attackmatrix']['url'] + '/search/?params=' + searchterms
                        async with httpx.AsyncClient(headers=headers) as session:
                            response = await session.get(APIENDPOINT)
                            json_response = response.json()
                            if json_response != 'null':
                                text = "AttackMatrix API search results for: `%s`\n" % ('`, `'.join(keywords))
                                text += "\n"
                                messages.append({'text': text})
                                numresults = 0
                                for matrix in json_response:
                                    if matrix in matrices:
                                        table = '**Matrix**: ' + matrix + '\n\n\n'
                                        for tableheader in tableheaders:
                                            table += '| %s ' % (tableheaders[tableheader],)
                                        table += '|\n'
                                        table += '|:- |:- |:- |\n'
                                        jsonmatrix = json_response[matrix]
                                        for category in jsonmatrix:
                                            if category in categories:
                                                jsonentries = jsonmatrix[category]
                                                for entry in jsonentries:
                                                    jsonentry = jsonentries[entry]
                                                    numresults += 1
                                                    name = jsonentry['name']
                                                    description = regex.sub(' ', jsonentry['description'])
                                                    if len(description)>80:
                                                        description = description[:80] + ' ...'
                                                    table += '| ' + category
                                                    table += ' | ' + jsonentry['name']
                                                    url = settings.APIURL['attackmatrix']['details']
                                                    url += '&matrix=' + matrix
                                                    url += '&cat=' + category
                                                    url += '&id=' + entry
                                                    table += '| [' + entry + '](' + url + ')'
                                                    table += ' |\n'
                                        messages.append({'text': table})
                                if numresults:
                                    text = 'Found ' + str(numresults) + ' match' + ('es' if numresults>1 else '') + ' for your search.'
                                    messages.append({'text': text})
                    else:
                        text = 'Invalid keyword(s).'
                        messages.append({'text': text})
                if querytype == 'mitre':
                    mitreid = keywords[0].upper()
                    if re.search(r"^[GMST][0-9]{4}(\.[0-9]{3})?$|^[T][A][0-9]{4}$", mitreid):
                        for matrix in matrices:
                            async with httpx.AsyncClient(headers=headers) as session:
                                APIENDPOINT = settings.APIURL['attackmatrix']['url'] + '/explore/' + matrix
                                response = await session.get(APIENDPOINT)
                                json_response = response.json()
                                if json_response != 'null':
                                    jsonmatrix = json_response[matrix]
                                    for category in jsonmatrix:
                                        if category in categories:
                                            jsonentries = jsonmatrix[category]
                                            if mitreid in jsonentries:
                                                details = jsonentries[mitreid]
                                                name = details['name']
                                                description = regex.sub(' ', details['description'])
                                                text = '**MITRE ID**: `' + mitreid + '` **Name**: `' + name + '`'
                                                text += '\n**Description:** `' + description + '`'
                                                messages.append({'text': text})
                                                APIENDPOINT = settings.APIURL['attackmatrix']['url']+'/explore/'+matrix+'/'+category+'/'+mitreid
                                                response = await session.get(APIENDPOINT)
                                                jsondetails = response.json()
                                                if len(jsondetails):
                                                    jsondetail = jsondetails[matrix][category][mitreid]
                                                    for detailcategory in jsondetail:
                                                        if category != detailcategory and detailcategory in categories:
                                                            table = '\n**Associated ' + detailcategory + '**'
                                                            table += '\n\n\n'
                                                            detailentries = jsondetail[detailcategory]
                                                            table += '| Reference | Name |\n'
                                                            table += '|:--------- |:---- |\n'
                                                            for detailentry in detailentries:
                                                                name = detailentries[detailentry]['name']
                                                                url = settings.APIURL['attackmatrix']['details']
                                                                url += '&matrix=' + matrix
                                                                url += '&cat=' + detailcategory
                                                                url += '&id=' + detailentry
                                                                table += '| [' + detailentry + '](' + url + ')'
                                                                table += ' | ' + name
                                                                table += ' |\n'
                                                            messages.append({'text': table})
                    else:
                        text = 'AttackMatrix: invalid MITRE TTP ID!'
                        messages.append({'text': text})
                if querytype == 'actoroverlap':
                    keywords = [_.upper() for _ in keywords]
                    searchterms = '&actor='.join([urllib.parse.quote(_) for _ in keywords])
                    if re.search(r"[\w\s,.\+\-]+", searchterms):
                        text = None
                        APIENDPOINT = settings.APIURL['attackmatrix']['url'] + '/actoroverlap/?actor=' + searchterms
                        async with httpx.AsyncClient(headers=headers) as session:
                            response = await session.get(APIENDPOINT)
                            json_response = response.json()
                            if json_response != 'null' and len(json_response):
                                numresults = 0
                                commonids = {}
                                actormatrices = {}
                                for actor in keywords:
                                    actormatrices[actor] = set()
                                    if actor in json_response['Actors']:
                                        for matrixname in json_response['Actors'][actor]['Matrices']:
                                            actormatrices[actor].add(matrixname)
                                categories = ('Matrices', 'Techniques', 'Subtechniques', 'Malwares', 'Tools', 'Mitigations', 'Tactics')
                                text = '**Actor Overlap** matrix for: `' + '`, `'.join(keywords) + '`'
                                text += '\n\n\n'
                                text += '| **MITRE ATT&CK** '
                                for actor in keywords:
                                    actorname = json_response['Actors'][actor]['name']
                                    text += '| **' + actor + '**: ' + actorname
                                text += ' |\n'
                                text += ('|:- ' * (len(keywords)+1)) + '|\n'
                                for actor in keywords:
                                    if actor in json_response['Actors']:
                                        jsonactors = json_response['Actors']
                                        jsoncategories = jsonactors[actor]
                                        for category in categories:
                                            if category in jsoncategories:
                                                detailcategories = collections.OrderedDict(sorted(jsoncategories[category].items()))
                                                for mitreid in detailcategories:
                                                    name = detailcategories[mitreid]['name']
                                                    text += '| **' + category + '** '
                                                    for otheractor in keywords:
                                                        if mitreid in jsonactors[otheractor][category]:
                                                            text += '| ' + mitreid
                                                            if category != 'Matrices':
                                                                text += ': ' + name
                                                                commonids[mitreid] = name
                                                                numresults += 1
                                                            text += ' '
                                                        else:
                                                            text += '| - '
                                                    text += '|\n'
                                    break
                                text += '\n\n'
                                text += 'Found ' + str(int(numresults/len(keywords))) + ' match' + ('es' if numresults>1 else '') + ' between the actors.'
                                # Build a list of unique TTPs for each actor
                                messages.append({'text': text})
                                actorttps = {}
                                for actor in keywords:
                                    actorttps[actor] = {}
                                    actorttps[actor]['ttps'] = {}
                                    for category in categories:
                                        actorttps[actor]['ttps'][category] = collections.OrderedDict()
                                    for actormatrix in actormatrices[actor]:
                                        APIENDPOINT = settings.APIURL['attackmatrix']['url'] + '/explore/' + actormatrix + '/Actors/' + actor
                                        async with httpx.AsyncClient(headers=headers) as session:
                                            response = await session.get(APIENDPOINT)
                                            json_response = response.json()
                                            if len(json_response):
                                                actorttps[actor]['name'] = json_response[actormatrix]['Actors'][actor]['name']
                                                for category in categories:
                                                    jsonactor = json_response[actormatrix]['Actors'][actor]
                                                    if category in jsonactor:
                                                        for ttp in jsonactor[category]:
                                                            ttpname = jsonactor[category][ttp]['name']
                                                            if not ttp in commonids:
                                                                actorttps[actor]['ttps'][category][ttp] = ttpname
                                text = '**Unique TTPs** matrix for: `' + '`, `'.join(keywords) + '`'
                                text += '\n\n\n'
                                text += '| **MITRE ATT&CK** '
                                for actor in keywords:
                                    text += '| **' + actor + '** ' + actorttps[actor]['name'] + ' '
                                text += '|\n'
                                text += ('|:- ' * (len(keywords)+1)) + '|\n'
                                count = 0
                                actoruniquettplist = {}
                                for actor in keywords:
                                    actoruniquettplist[actor] = {}
                                    actoruniquettplist[actor]['name'] = actorttps[actor]['name']
                                    for category in categories:
                                        if category in actorttps[actor]['ttps']:
                                            actoruniquettplist[actor][category] = list(actorttps[actor]['ttps'][category].items())
                                for category in categories:
                                    maxcount = 0
                                    for actor in keywords:
                                        if len(actoruniquettplist[actor][category])>maxcount:
                                            maxcount = len(actoruniquettplist[actor][category])
                                    while count<maxcount:
                                        text += '| **' + category + '** '
                                        for actor2 in keywords:
                                            if count<len(actoruniquettplist[actor2][category]):
                                                mitreid, name = actoruniquettplist[actor2][category][count]
                                                text += '| ' + mitreid + ': ' + name + ' '
                                            else:
                                                text += '| - '
                                        text += '|\n'
                                        count += 1
                                    count = 0
                                messages.append({'text': text})
                                filename = '-'.join(keywords) + '.png'
                                graph = graphviz.Digraph(comment=filename, format='png')
                                graph.attr(layout='sfdp', overlap='prism')
                                # Create the actor nodes
                                for actor in actorttps:
                                    graph.node(actor,
                                               actorttps[actor]['name'],
                                               style='filled',
                                               fillcolor='#000080',
                                               fontcolor='white')
                                    for category in actorttps[actor]['ttps']:
                                        for ttp in actorttps[actor]['ttps'][category].items():
                                            mitreid, name = ttp
                                            contents = mitreid + '\n' + name
                                            graph.node(mitreid,
                                                       contents,
                                                       shape='box',
                                                       style='filled',
                                                       fillcolor='#800000',
                                                       fontcolor='white')
                                            graph.edge(actor, mitreid)
                                # Create the nodes for the TTPs they have in common
                                for commonid in commonids:
                                    contents = commonid + '\n' + commonids[commonid]
                                    graph.node(commonid,
                                               contents,
                                               shape='box',
                                               style='filled',
                                               fillcolor='#008000',
                                               fontcolor='white')
                                    for actor in actorttps:
                                        graph.edge(actor, commonid)
                                bytes = graph.pipe()
                                messages.append({
                                    'text': 'Graphical representation of overlap:\n', 'uploads': [{'filename': filename, 'bytes': bytes}]
                                })
                            else:
                                messages.append({'text': 'AttackMatrix: invalid MITRE Actor ID or no overlap.\n'})
                if querytype == 'ttpoverlap':
                    keywords = [keyword.upper() for keyword in keywords]
                    searchterms = '&ttp='.join([urllib.parse.quote(_) for _ in keywords])
                    if re.search(r"[\w\s,.\+\-]+", searchterms):
                        text = None
                        APIENDPOINT = settings.APIURL['attackmatrix']['url'] + '/ttpoverlap/?ttp=' + searchterms
                        async with httpx.AsyncClient(headers=headers) as session:
                            response = await session.get(APIENDPOINT)
                            json_response = response.json()
                            numresults = 0
                            actornames = set()
                            if json_response != 'null' and len(json_response):
                                for matrix in json_response:
                                    numresults += len(json_response[matrix]['Actors'])
                                    for actor in json_response[matrix]['Actors']:
                                        actornames.add(actor)
                                if numresults>settings.MAXRESULTS:
                                    text = 'AttackMatrix: More than ' + str(settings.MAXRESULTS) + ' actors match your TTP set, '
                                    text += 'making the resulting data set too large to be useful. Narrow down your selection by '
                                    text += 'either adding more TTPs or selecting more specific TTPs.\n'
                                    text += 'You are currently matching ' + str(len(actornames)) + ' actors: `' + '`, `'.join(actornames) + '`.'
                                    messages.append({'text': text})
                                else:
                                    numresults = 0
                                    actors = collections.OrderedDict()
                                    categories = ('Matrices', 'Techniques', 'Subtechniques', 'Malwares', 'Tools', 'Mitigations', 'Tactics')
                                    text = '**TTP Overlap** matrix for: `' + '`, `'.join(keywords) + '`'
                                    text += '\n\n\n'
                                    text += '| **MITRE ATT&CK** '
                                    commonids = collections.OrderedDict()
                                    actoruniquettplist = {}
                                    for matrix in matrices:
                                        if matrix in json_response:
                                            matrix = json_response[matrix]
                                            for actor in matrix['Actors']:
                                                actorname = matrix['Actors'][actor]['name']
                                                actors[actor] = actorname
                                    for actor in actors:
                                        text += '| **' + actor + '**: ' + actors[actor] + ' '
                                        if not actor in actoruniquettplist:
                                            actoruniquettplist[actor] = {}
                                    text += '|\n'
                                    text += ('|:- ' * (len(actors)+1)) + '|\n'
                                    for matrix in matrices:
                                        if matrix in json_response:
                                            matrix = json_response[matrix]
                                            for jsonactor in matrix['Actors']:
                                                for jsonactorcategory in matrix['Actors'][jsonactor]:
                                                    if not jsonactorcategory in actoruniquettplist[actor]:
                                                        actoruniquettplist[jsonactor][jsonactorcategory] = {}
                                                    if jsonactorcategory in categories:
                                                        if not jsonactorcategory in commonids:
                                                            commonids[jsonactorcategory] = {}
                                                        for jsonactorttp in matrix['Actors'][jsonactor][jsonactorcategory]:
                                                            name = matrix['Actors'][jsonactor][jsonactorcategory][jsonactorttp]['name']
                                                            if jsonactorttp in keywords:
                                                                commonids[jsonactorcategory][jsonactorttp] = name
                                                            else:
                                                                actoruniquettplist[jsonactor][jsonactorcategory][jsonactorttp] = name
                                    for commoncategory in commonids:
                                        for commonid in commonids[commoncategory]:
                                            text += '| **' + commoncategory + '** '
                                            contents = '| **' + commonid + '**: ' + commonids[commoncategory][commonid] + ' '
                                            text += (contents) * (len(actors))
                                            text += '|\n'
                                    messages.append({'text': text})
                                    for actor in actors:
                                        text = '**Unique TTPs** for **' + actor + '**: ' + actors[actor]
                                        text += '\n\n\n'
                                        text += '| **MITRE ATT&CK** | **' + actor + '**: ' + actors[actor] + '\n'
                                        text += '|:- |:- |\n'
                                        for category in categories:
                                            if category in actoruniquettplist[actor]:
                                                if len(actoruniquettplist[actor][category])>0:
                                                    text += '| **' + category + '** | '
                                                    for uniquettp in actoruniquettplist[actor][category]:
                                                        name = actoruniquettplist[actor][category][uniquettp]
                                                        text += '**' + uniquettp +'**: ' + name + ', '
                                                    text = text[:-2]
                                                    text += '|\n'
                                        text += '\n'
                                        messages.append({'text': text})
                                    # Digraph
                                    filename = '-'.join(keywords) + '.png'
                                    graph = graphviz.Digraph(comment=filename, format='png')
                                    graph.attr(layout='sfdp', overlap='prism')
                                    # Create the actor nodes
                                    for actor in actors:
                                        contents = actor + '\n' + actors[actor]
                                        graph.node(actor,
                                                   contents,
                                                   style='filled',
                                                   fillcolor='#000080',
                                                   fontcolor='white')
                                        for category in categories:
                                            if category in actoruniquettplist[actor]:
                                                if len(actoruniquettplist[actor][category])>0:
                                                    for ttp in actoruniquettplist[actor][category].items():
                                                        mitreid, name = ttp
                                                        contents = mitreid + '\n' + name
                                                        graph.node(mitreid,
                                                                   contents,
                                                                   shape='box',
                                                                   style='filled',
                                                                   fillcolor='#800000',
                                                                   fontcolor='white')
                                                        graph.edge(actor, mitreid)
                                    # Create the nodes for the TTPs they have in common
                                    for category in categories:
                                        if category in commonids:
                                            for ttp in commonids[category].items():
                                                mitreid, name = ttp
                                                contents = mitreid + '\n' + name
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
                                        'text': 'AttackMatrix: no results found for `' + '`, `'.join(keywords) + '`.'
                                    })
                                else:
                                    messages.append({
                                        'text': 'AttackMatrix: you must specify at least two TTPs!'
                                    })
        except Exception as e:
            messages.append({'text': 'An error occurred querying AttackMatrix:\nError: ' + str(e)})
        finally:
            return {'messages': messages}
