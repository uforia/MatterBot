#!/usr/bin/env python3

import datetime
import math
import random
import re
import requests
import traceback
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

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    querytypes = ['ip', 'credits', 'account', 'host', 'count', 'search']
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
            return
            #return {'messages': [
            #    {'text': 'Please specify one of these query types: `' + '`, `'.join(querytypes) + '`'}
            #]}
        headers = {
            'Content-Type': settings.CONTENTTYPE,
        }
        if len(settings.APIURL['shodan']['key']):
            apikey = random.choice(settings.APIURL['shodan']['key'])
        else:
            return
        try:
            messages = []
            if querytype == 'ip':
                ip = params[0].split(':')[0].replace('[', '').replace(']', '')
                text = 'Shodan `%s` search for `%s`: ' % (querytype, ip)
                if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", ip):
                    APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/%s' % (ip,)
                    if apikey:
                        APIENDPOINT += '?key=%s' % (apikey,)
                    with requests.get(APIENDPOINT, headers=headers) as response:
                        json_response = response.json()
                        if 'error' in json_response:
                            error = json_response['error']
                            if 'No information available' in error:
                                return
                            else:
                                return {'messages': [{'text': 'An error occurred searching Shodan: ' + error}]}
                        if 'matches' in json_response:
                            total = len(json_response['matches'])
                            if total==0:
                                return
                        text += '\n\n'
                        text += '| Hostname(s) | Service | Port | Proto | Vulns | SSL/TLS | Product | Banner |\n'
                        text += '|:----------- |--------:| ----:| -----:| -----:| -------:|:------- |:-------|\n'
                        if 'data' in json_response:
                            json_data = json_response['data']
                            for service in json_data:
                                result = {}
                                fields = ('hostnames', 'port', 'transport', 'product', 'data')
                                for field in fields:
                                    if field in service:
                                        if isinstance(service[field],list):
                                            result[field] = ', '.join(service[field])
                                        else:
                                            result[field] = str(service[field])
                                        if not len(result[field]):
                                            result[field] = ' - '
                                    else:
                                        result[field] = ' - '
                                result['name'] = service['_shodan']['module']
                                if 'ssl' in service:
                                    if 'match' in service['ssl']:
                                        result['ssl'] = service['ssl']['cipher']['version']
                                else:
                                    result['ssl'] = ' No '
                                if 'vulns' in service['opts']:
                                    result['vulns'] = str(len(service['opts']['vulns']))
                                else:
                                    result['vulns'] = '0'
                                for field in ('product', 'data'):
                                    if field in result:
                                        result[field] = regex.sub(' ', result[field])
                                        if len(result[field])>60:
                                            if field == 'data':
                                                result[field] = "".join(c for c in result[field] if c.isalnum() or c.isspace() or c in ['.',';'])
                                            result[field] = result[field][:60] + ' [...]'
                                fields = ('hostnames', 'name', 'port', 'transport', 'vulns', 'ssl', 'product', 'data')
                                for field in fields:
                                    if field in result:
                                        text += '| ' + result[field].encode('ascii','ignore').decode() + ' '
                                    else:
                                        text += '| - '
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
                    APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/search?'
                    if apikey:
                        APIENDPOINT += 'key=%s' % (apikey,)
                    APIENDPOINT += '&query=%s' % (host,)
                    with requests.get(APIENDPOINT, headers=headers) as response:
                        json_response = response.json()
                        if 'matches' in json_response:
                            total = len(json_response['matches'])
                            if total==0:
                                return
                        if 'error' in json_response:
                            error = json_response['error']
                            if 'No information available' in error:
                                return
                            else:
                                return {'messages': [{'text': 'An error occurred searching Shodan: ' + error}]}
                        text += '\n\n'
                        text += '| Hostname(s) | Service | Port | Proto | Vulns | SSL/TLS | Product | Banner |\n'
                        text += '|:----------- |--------:| ----:| -----:| -----:| -------:|:------- |:-------|\n'
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
                                    if 'vulns' in match:
                                        result['vulns'] = str(len(match['vulns']))
                                    else:
                                        result['vulns'] = '0'
                                    for field in ('product', 'data'):
                                        if field in result:
                                            result[field] = regex.sub(' ', result[field])
                                            if len(result[field])>60:
                                                if field == 'data':
                                                    result[field] = "".join(c for c in result[field] if c.isalnum() or c.isspace() or c in ['.',';'])
                                                result[field] = result[field][:60] + ' [...]'
                                    fields = ('hostnames', 'name', 'port', 'transport', 'vulns', 'ssl', 'product', 'data')
                                    for field in fields:
                                        text += '| ' + result[field].encode('ascii','ignore').decode() + ' '
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
                APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/count'
                if apikey:
                    APIENDPOINT += '?key=%s' % (apikey,)
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
                with requests.get(APIENDPOINT, headers=headers) as response:
                    json_response = response.json()
                    if 'error' in json_response:
                        error = json_response['error']
                        return {'messages': [{'text': 'An error occurred, wrong/missing API key? Error: ' + error}]}
                    if 'total' in json_response:
                        total = json_response['total']
                        if total>0:
                            text += ', result(s): `' + str(total) + '`:\n'
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
                                    banner = regex.sub('|', match['data'][:60]).encode('ascii','ignore').decode()
                                    banner = "".join(c for c in banner if c.isalnum() or c.isspace() or c in ['.',';'])
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
                APIENDPOINT = settings.APIURL['shodan']['url'] + '/shodan/host/search'
                if apikey:
                    APIENDPOINT += '?key=%s' % (apikey,)
                if not len(params):
                    return {'messages': [{'text': 'Please specify what to search for.'}]}
                query = set()
                facets = set()
                filters = set()
                limit = 100
                uploads = []
                try:
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
                except Exception as e:
                    return {'messages': [{'text': e}]}
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
                    with requests.get(PAGEENDPOINT, headers=headers) as response:
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
                                text += '\nReturning up to 10 matches from the first page only; download the JSON file(s) for all ' + str(total) + ' result(s):'
                                text += '\n\n'
                                text += '| IP Address | Hostname(s) | Service | Port | Proto | Vulns | SSL/TLS | Product | Banner |\n'
                                text += '| ---------: | :---------- | ------: | ---: | ----: | ----: | ------: | :------ | :---- -|\n'
                                table_header_displayed = True
                            for match in matches[:10]:
                                result = {}
                                fields = ('ip_str', 'hostnames', 'port', 'transport', 'product', 'data')
                                for field in fields:
                                    if field in match:
                                        if isinstance(match[field],list):
                                            combined = ', '.join(str(_) for _ in match[field])
                                            if len(combined):
                                                result[field] = ', '.join(str(_) for _ in match[field])
                                            else:
                                                result[field] = ' - '
                                        else:
                                            if field == 'data':
                                                result[field] = "".join(c for c in str(match[field]) if c.isalnum() or c.isspace() or c in ['.',';'])
                                            else:
                                                result[field] = str(match[field])
                                        if not len(str(match[field])):
                                            result = ' - '
                                    else:
                                        result[field] = ' - '
                                result['name'] = match['_shodan']['module']
                                if 'ssl' in match:
                                    if 'cipher' in match['ssl']:
                                        result['ssl'] = match['ssl']['cipher']['version']
                                else:
                                    result['ssl'] = ' No '
                                if 'vulns' in match:
                                    result['vulns'] = str(len(match['vulns']))
                                else:
                                    result['vulns'] = '0'
                                for field in ('product', 'data'):
                                    if field in result:
                                        result[field] = regex.sub(' ', result[field])
                                        if len(str(result[field]))>60:
                                            result[field] = result[field][:60] + ' [...]'
                                fields = ('ip_str', 'hostnames', 'name', 'port', 'transport', 'vulns', 'ssl', 'product', 'data')
                                for field in fields:
                                    if field in result:
                                        text += '| ' + result[field] + ' '
                                text += ' |\n'
                            uploads.append({'filename': 'shodan-'+querytype+'-page-'+str(page)+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json', 'bytes': response.content})
                        elif page==1:
                            messages.append({'text': '\nNo matches.'})
                if table_header_displayed:
                    messages.append({'text': text})
                    if len(uploads):
                        messages.append({'text': 'Shodan JSON output:', 'uploads': uploads})
            if querytype == 'credits' or querytype == 'account':
                text = 'Shodan API account credits (remaining/total):'
                APIENDPOINT = settings.APIURL['shodan']['url'] + '/api-info'
                if apikey:
                    APIENDPOINT += '?key=%s' % (apikey,)
                with requests.get(APIENDPOINT, headers=headers) as response:
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
        except ValueError as e:
            return {'messages': [
                {'text': 'Seems like Shodan did not return something like JSON: `%s`' % (response.content,)}
            ]}
        except Exception as e:
            return {'messages': [
                {'text': 'A Python error occurred searching Shodan:\nError: `%s`' % (traceback.format_exc(),)}
            ]}
