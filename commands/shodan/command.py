#!/usr/bin/env python3

import datetime
import httpx
import json
import math
import random
import re
import urllib
from pathlib import Path
try:
    from commands.shodan import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/shodan/settings.py').is_file():
        try:
            from commands.shodan import settings
        except ModuleNotFoundError: # local test run
            import settings

async def process(command, channel, username, params):
    # Methods to query the current API account info (credits etc.)
    querytypes = ['ip', 'credits', 'host', 'count', 'search']
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    if len(params)>0:
        querytype = params[0]
        if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", querytype.replace('[', '').replace(']', '')):
            params = [querytype]
            querytype = 'ip'
        elif re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", querytype.replace('[', '').replace(']', '')):
            params = [querytype]
            querytype = 'host'
        else:
            params = params[1:]
        if not querytype in querytypes:
            return {'messages': [
                {'text': 'Please specify one of these query types: `' + '`, `'.join(querytypes) + '`'}
            ]}
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        apikey = random.choice(settings.APIURL['shodan']['key'])
        try:
            messages = []
            if querytype == 'ip':
                ip = params[0].split(':')[0].replace('[', '').replace(']', '')
                text = 'Shodan `%s` search for `%s`:' % (querytype, ip)
                if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", ip):
                    APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/%s?key=%s' % (ip, apikey)
                    async with httpx.AsyncClient(headers=headers) as session:
                        response = await session.get(APIENDPOINT)
                        json_response = response.json()
                        if 'error' in json_response:
                            error = json_response['error']
                            if 'No information available' in error:
                                return {'messages': [{'text': 'No results found.'}]}
                            else:
                                return {'messages': [{'text': 'An error occurred searching Shodan: ' + error}]}
                        if 'total' in json_response:
                            total = json_response['total']
                            if total==0:
                                return {'messages': [{'text': 'No results found.'}]}
                        text += '\n\n'
                        text += '| Hostname(s) | Service | Port | Proto | SSL/TLS | Product | Banner |\n'
                        text += '| -----------:|--------:| ----:| -----:| -------:|:------- |:-------|\n'
                        if 'data' in json_response:
                            json_data = json_response['data']
                            for service in json_data:
                                result = {}
                                fields = ('hostnames', 'port', 'transport', 'product', 'data')
                                for field in fields:
                                    if field in service:
                                        if isinstance(service[field],list):
                                            if len(service[field]):
                                                result[field] = ', '.join(service[field])
                                            else:
                                                result[field] = ' - '
                                        else:
                                            result[field] = str(service[field])
                                    else:
                                        result[field] = ' - '
                                result['name'] = service['_shodan']['module']
                                if 'ssl' in service:
                                    result['ssl'] = service['ssl']['cipher']['version']
                                else:
                                    result['ssl'] = ' No '
                                for field in ('product', 'data'):
                                    if field in result:
                                        result[field] = regex.sub(' ', result[field])
                                        if len(result[field])>60:
                                            result[field] = result[field][:60] + ' [...]'
                                fields = ('hostnames', 'name', 'port', 'transport', 'ssl', 'product', 'data')
                                for field in fields:
                                    text += '| ' + result[field] + ' '
                                text += ' |\n'
                        messages.append({'text': text})
                        messages.append({'text': 'Shodan JSON output:', 'uploads': [
                                            {'filename': 'shodan-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content}
                                        ]})
                else:
                    text += ' invalid IP address!'
                    messages.append({'text': text})
            if querytype == 'host':
                host = params[0].split(':')[0].replace('[', '').replace(']', '')
                text = 'Shodan `%s` search for `%s`:' % (querytype, host)
                if re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", host):
                    APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/search?key=%s&query=%s' % (apikey, host)
                    async with httpx.AsyncClient(headers=headers) as session:
                        response = await session.get(APIENDPOINT)
                        json_response = response.json()
                        if 'total' in json_response:
                            total = json_response['total']
                            if total==0:
                                return {'messages': [{'text': 'No results found.'}]}
                        if 'error' in json_response:
                            error = json_response['error']
                            if 'No information available' in error:
                                return {'messages': [{'text': 'No results found.'}]}
                            else:
                                return {'messages': [{'text': 'An error occurred searching Shodan: ' + error}]}
                        text += '\n\n'
                        text += '| Hostname(s) | Service | Port | Proto | SSL/TLS | Product | Banner |\n'
                        text += '| -----------:|--------:| ----:| -----:| -------:|:------- |:-------|\n'
                        if 'matches' in json_response:
                            matches = json_response['matches']
                            if len(matches):
                                for match in matches:
                                    result = {}
                                    fields = ('hostnames', 'port', 'transport', 'product', 'data')
                                    for field in fields:
                                        if field in match:
                                            if isinstance(match[field],list):
                                                if len(match[field]):
                                                    result[field] = ', '.join(match[field])
                                                else:
                                                    result[field] = ' - '
                                            else:
                                                result[field] = str(match[field])
                                        else:
                                            result[field] = ' - '
                                    result['name'] = match['_shodan']['module']
                                    if 'ssl' in match:
                                        result['ssl'] = match['ssl']['cipher']['version']
                                    else:
                                        result['ssl'] = ' No '
                                    for field in ('product', 'data'):
                                        if field in result:
                                            result[field] = regex.sub(' ', result[field])
                                            if len(result[field])>60:
                                                result[field] = result[field][:60] + ' [...]'
                                    fields = ('hostnames', 'name', 'port', 'transport', 'ssl', 'product', 'data')
                                    for field in fields:
                                        text += '| ' + result[field] + ' '
                                    text += ' |\n'
                            else:
                                text += '\nNo matches.'
                        messages.append({'text': text})
                        messages.append({'text': 'Shodan JSON output:', 'uploads': [
                                            {'filename': 'shodan-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content}
                                        ]})
                else:
                    text += ' invalid hostname!'
                    messages.append({'text': text})
            if querytype == 'count':
                APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/count?key=%s' % (apikey,)
                if not len(params):
                    return {'messages': [{'text': 'Please specify what to search for.'}]}
                query = set()
                facets = set()
                filters = set()
                for param in params:
                    if param.startswith('query:'):
                        for value in param.replace('query:', '').split(','):
                            query.add(value.replace('[', '').replace(']', '').replace('hxxp','http'))
                    if param.startswith('filters:'):
                        for value in param.replace('filters:', '').split(','):
                            filters.add(value)
                    if param.startswith('facets:'):
                        for value in param.replace('facets:', '').split(','):
                            facets.add(value)
                if not len(query):
                    return {'messages': [{'text': 'Please specify what to search for.'}]}
                query = urllib.parse.quote(' '.join(query))
                APIENDPOINT += '&query=' + query
                text = 'Shodan `' + querytype + '` search for query: `' + urllib.parse.unquote(query) + '`'
                if len(filters):
                    filters = urllib.parse.quote(' '.join(filters))
                    APIENDPOINT += '%20'
                    APIENDPOINT += filters
                    text += ', filters: `' + urllib.parse.unquote(filters) + '`'
                if len(facets):
                    facets = urllib.parse.quote(','.join(facets))
                    APIENDPOINT += '&facets=' + facets
                    text += ', facets: `' + urllib.parse.unquote(facets) + '`'
                async with httpx.AsyncClient(headers=headers) as session:
                    response = await session.get(APIENDPOINT)
                    json_response = response.json()
                    if 'error' in json_response:
                        error = json_response['error']
                        return {'messages': [{'text': 'An error occurred, wrong/missing API key? Error: ' + error}]}
                    if 'total' in json_response:
                        total = json_response['total']
                        if total>0:
                            text += ', results: `' + str(total) + '`:\n'
                    if 'facets' in json_response:
                        facets = json_response['facets']
                        for facet in facets:
                            if len(facets[facet]):
                                text += '\n**Grouped by**: `' + facet + '`\n\n'
                                text += '| Value | Count |\n'
                                text += '| ----- | -----:|\n'
                                for entry in facets[facet]:
                                    count, value = entry['count'], entry['value']
                                    text += '| ' + value + ' | ' + str(count) + ' |\n'
                    if 'matches' in json_response:
                        matches = json_response['matches']
                        if len(matches):
                            for match in matches:
                                data = None
                                banner = None
                                product = None
                                ssl = None
                                name = match['_shodan']['module']
                                port = str(match['port'])
                                transport = match['transport']
                                if 'hostnames' in match:
                                    hostnames = match['hostnames']
                                if 'data' in match:
                                    banner = regex.sub('|', match['data'][:60])
                                    if len(match['data'])>60:
                                        banner += ' [...]'
                                if 'product' in match:
                                    product = regex.sub('', match['product'][:80])
                                    if len(match['product'])>80:
                                        product += ' [...]'
                                if 'ssl' in match:
                                    ssl = True
                                text += '\n**Service**: ' + name.upper() + ' '
                                text += '| **Port**: `' + port + '`/`' + transport + '` '
                                if hostnames:
                                    text += '| **Hostname(s)**: `' + '`, `'.join(hostnames) + '` '
                                if ssl:
                                    text += '(SSL/TLS) '
                                if product:
                                    text += '| **Product**: `' + product + '`'
                                if banner:
                                    text += '| **Banner**: `' + banner + '`'
                        else:
                            text += 'No details.'
                    messages.append({'text': text})
                    messages.append({'text': 'Shodan JSON output:', 'uploads': [
                                        {'filename': 'shodan-'+querytype+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content}
                                    ]})
            if querytype == 'search':
                APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/search?key=%s' % (apikey,)
                if not len(params):
                    return {'messages': [{'text': 'Please specify what to search for.'}]}
                query = set()
                facets = set()
                filters = set()
                limit = 100
                uploads = []
                for param in params:
                    if param.startswith('query:'):
                        for value in param.replace('query:', '').split(','):
                            query.add(value.replace('[', '').replace(']', '').replace('hxxp','http'))
                    if param.startswith('filters:'):
                        for value in param.replace('filters:', '').split(','):
                            filters.add(value)
                    if param.startswith('facets:'):
                        for value in param.replace('facets:', '').split(','):
                            facets.add(value)
                    if param.startswith('limit:'):
                        limit = param.split(':')[1]
                try:
                    pages = math.floor(int(limit)/100)
                    if int(limit) % 100:
                        pages += 1
                except ValueError:
                    return {'messages': [{'text': 'Invalid limit.'}]}
                if not len(query):
                    return {'messages': [{'text': 'Please specify what to search for.'}]}
                query = urllib.parse.quote(' '.join(query))
                APIENDPOINT += '&query=' + query
                text = 'Shodan `' + querytype + '` search for query: `' + urllib.parse.unquote(query) + '`'
                if len(filters):
                    filters = urllib.parse.quote(' '.join(filters))
                    APIENDPOINT += '%20'
                    APIENDPOINT += filters
                    text += ', filters: `' + urllib.parse.unquote(filters) + '`'
                if len(facets):
                    facets = urllib.parse.quote(','.join(facets))
                    APIENDPOINT += '&facets=' + facets
                    text += ', facets: `' + urllib.parse.unquote(facets) + '`'
                table_header_displayed = False
                for page in range(1,pages+1):
                    PAGEENDPOINT = APIENDPOINT+'&page='+str(page) if page>1 else APIENDPOINT
                    async with httpx.AsyncClient(headers=headers) as session:
                        response = await session.get(PAGEENDPOINT)
                        json_response = response.json()
                        if 'error' in json_response:
                            error = json_response['error']
                            return {'messages': [{'text': 'An error occurred, wrong/missing API key? Error: ' + error}]}
                        if 'facets' in json_response:
                            facets = json_response['facets']
                            for facet in facets:
                                if len(facets[facet]):
                                    text += '\n**Grouped by**: `' + facet + '`\n\n'
                                    text += '| Value | Count |\n'
                                    text += '| ----- | -----:|\n'
                                    for entry in facets[facet]:
                                        count, value = entry['count'], entry['value']
                                        text += '| ' + value + ' | ' + str(count) + ' |\n'
                        if 'matches' in json_response:
                            matches = json_response['matches']
                            if len(matches) and page==1 and not table_header_displayed:
                                total = json_response['total']
                                text += '\nReturning up to 10 matches from the first page only; download the JSON file(s) for all ' + str(total) + ' results:'
                                text += '\n\n'
                                text += '| Hostname(s) | Service | Port | Proto | SSL/TLS | Product | Banner |\n'
                                text += '| -----------:|--------:| ----:| -----:| -------:|:------- |:-------|\n'
                                table_header_displayed = True
                            for match in matches[:10]:
                                result = {}
                                fields = ('hostnames', 'port', 'transport', 'product', 'data')
                                for field in fields:
                                    if field in match:
                                        if isinstance(match[field],list):
                                            if len(match[field]):
                                                result[field] = ', '.join(match[field])
                                            else:
                                                result[field] = ' - '
                                        else:
                                            result[field] = str(match[field])
                                    else:
                                        result[field] = ' - '
                                result['name'] = match['_shodan']['module']
                                if 'ssl' in match:
                                    result['ssl'] = match['ssl']['cipher']['version']
                                else:
                                    result['ssl'] = ' No '
                                for field in ('product', 'data'):
                                    if field in result:
                                        result[field] = regex.sub(' ', result[field])
                                        if len(result[field])>60:
                                            result[field] = result[field][:60] + ' [...]'
                                fields = ('hostnames', 'name', 'port', 'transport', 'ssl', 'product', 'data')
                                for field in fields:
                                    text += '| ' + result[field] + ' '
                                text += ' |\n'
                            uploads.append({'filename': 'shodan-'+querytype+'-page-'+str(page)+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content})
                            messages.append({'text': text})
                            messages.append({'text': 'Shodan JSON output:', 'uploads': uploads})
                        elif page==1:
                            messages.append({'text': '\nNo matches.'})
            if querytype == 'credits':
                text = 'Shodan API account credits (remaining/total):'
                APIENDPOINT = settings.APIURL['shodan']['url'] + '/api-info?key=%s' % (apikey,)
                async with httpx.AsyncClient(headers=headers) as session:
                    response = await session.get(APIENDPOINT)
                    json_response = response.json()
                    if 'error' in json_response:
                        error = json_response['error']
                        return {'messages': [{'text': 'An error occurred, wrong/missing API key? Error: ' + error}]}
                    usage_limits = json_response['usage_limits']
                    plan = json_response['plan']
                    https = 'Yes' if json_response['https'] else 'No'
                    telnet = 'Yes' if json_response['telnet'] else 'No'
                    text += '\n**Plan**: ' + plan + ', **HTTPS**: ' + https + ', **Telnet**: ' + telnet
                    query_credits_remaining = str(json_response['query_credits'])
                    query_credits_limit = str(usage_limits['query_credits'])
                    text += '\n**Query**: ' + query_credits_remaining + '/' + query_credits_limit
                    scan_credits_remaining = str(json_response['scan_credits'])
                    scan_credits_limit = str(usage_limits['scan_credits'])
                    text += '\n**Scan**: ' + scan_credits_remaining + '/' + scan_credits_limit
                    monitored_ips_remaining = str(json_response['monitored_ips'])
                    monitored_ips_limit = str(usage_limits['monitored_ips'])
                    text += '\n**Monitor**: ' + monitored_ips_remaining + '/' + monitored_ips_limit
                    messages.append({'text': text})
            return {'messages': messages}
        except Exception as e:
            return {'messages': [
                {'text': 'A Python error occurred searching Shodan:\nError:' + e}
            ]}
