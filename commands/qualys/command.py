#!/usr/bin/env python3

import collections
import datetime
import json
import re
import requests
import sys
import traceback
import urllib.parse
from pathlib import Path
try:
    from commands.qualys import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/qualys/settings.py').is_file():
        try:
            from commands.qualys import settings
        except ModuleNotFoundError: # local test run
            import settings

def getToken():
    try:
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        username = urllib.parse.quote(settings.APIURL['qualys']['username'])
        password = urllib.parse.quote(settings.APIURL['qualys']['password'])
        data = 'username=%s&password=%s&token=true' % (username,password)
        with requests.post(settings.APIURL['qualys']['jwt'], headers=headers, data=data) as response:
            content = response.content.decode()
            if 'Authentication Failure' in content:
                return None
            else:
                return content
    except:
        return None

def normalizeFields(filters: list):
    normalization = { # Simplify handling the case sensitivity of the CSAM API (seriously!?)
        'assetname': 'assetName',
        'dnsname': 'dnsName',
        'operatingsystem': 'operatingSystem',
    }
    for filter in filters:
        if filter.lower() in normalization:
            filters = list(map(lambda _: _.replace(filter,normalization[filter.lower()]),filters))
    return filters

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    messages = []
    querytypes = ['domain','host','ip','software','sw']
    stripchars = '`\\[\\]\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    try:
        if len(params)>0:
            querytype = regex.sub('',params[0].lower())
            if querytype not in querytypes:
                return
            if querytype:
                token = getToken()
                if token:
                    headers = {
                        'Accept-Encoding': settings.CONTENTTYPE,
                        'Content-Type': settings.CONTENTTYPE,
                        'Authorization': 'Bearer %s' % (token,),
                    }
                    if querytype in ('publisher','software','sw'):
                        querytype = 'software'
                    filtermap = {
                        'domain': {
                            'filters': [
                            {
                                'field': 'asset.domain',
                                'operator': 'CONTAINS',
                                'value': None,
                            },
                            ],
                            'operation': 'OR',
                        },
                        'ip': {
                            'filters': [
                            {
                                'field': 'interfaces.address',
                                'operator': 'EQUALS',
                                'value': None,
                            },
                            ],
                        },
                        'host': {
                            'filters': [
                            {
                                'field': 'asset.name',
                                'operator': 'EQUALS',
                                'value': None,
                            },
                            ],
                            'operation': 'OR',
                        },
                        'software': {
                            'filters': [
                            {
                                'field': 'software.name',
                                'operator': 'CONTAINS',
                                'value': None,
                            },
                            {
                                'field': 'software.product',
                                'operator': 'CONTAINS',
                                'value': None,
                            },
                            {
                                'field': 'software.publisher',
                                'operator': 'CONTAINS',
                                'value': None,
                            },
                            ],
                            'operation': 'OR',
                        },
                    }
                    query = ' '.join(params[1:])
                    completeAPIurl = settings.APIURL['qualys']['csam']
                    for filter in filtermap[querytype]['filters']:
                        filter['value'] = query.lower()
                    if querytype in ('host',):
                        filtermap[querytype]['filters'].append({
                            'field': 'asset.name',
                            'operator': 'CONTAINS',
                            'value': query.upper(),
                        })
                    if querytype in ('domain',):
                        filtermap[querytype]['filters'].append({
                            'field': 'asset.domain',
                            'operator': 'CONTAINS',
                            'value': query.upper(),
                        })
                    if querytype == 'software':
                        completeAPIurl += '?includeFields=assetName,dnsName,address,software,tag'
                    jsonfilter = json.dumps(filtermap[querytype])
                    with requests.post(completeAPIurl, headers=headers, data=jsonfilter) as response:
                        try:
                            if len(response.content):
                                json_response = json.loads(response.content)
                                if 'responseCode' in json_response:
                                    if json_response['responseCode'].lower() != 'success':
                                        messages.append({'text': 'The provided Qualys CSAM query did not return a successful result.'})
                                    else:
                                        displayfields = collections.OrderedDict({
                                            'assetName': 'Name',
                                            'address': 'Network',
                                            'dnsName': 'Hostname',
                                            'hardware': 'Hardware',
                                            'operatingSystem': 'OS',
                                            'openPortListData': 'Services',
                                            'tagList': 'Tags',
                                            'sensorLastUpdatedDate': 'Last Update',
                                        })
                                        try:
                                            if querytype == 'domain':
                                                messages.append({'text': 'Currently not implemented due to Qualys API EASM particularities.'})
                                            if querytype == 'software':
                                                if 'assetListData' in json_response:
                                                    assetListData = json_response['assetListData']
                                                    if 'asset' in assetListData:
                                                        assets = assetListData['asset']
                                                        if len(assets):
                                                            if 'hasMore' in json_response:
                                                                hasMore = int(json_response['hasMore'])
                                                                while hasMore == 1:
                                                                    lastSeenAssetId = json_response['lastSeenAssetId']
                                                                    paginationAPIurl = completeAPIurl + f"&lastSeenAssetId={lastSeenAssetId}"
                                                                    with requests.post(paginationAPIurl, headers=headers, data=jsonfilter) as response:
                                                                        json_response = json.loads(response.content)
                                                                        assets += json_response['assetListData']['asset']
                                                                        hasMore = int(json_response['hasMore'])
                                                                        lastSeenAssetId = json_response['lastSeenAssetId']
                                                            csvFile = '"IP Address","Hostname","Asset Name","Product","Version","Tags"\n'
                                                            productlist = {}
                                                            message = '\n**Qualys CSAM query results**'
                                                            message += '\n*Querytype*: `%s` | *Query*: `%s` | *Assets*: `%s` ' % (querytype,query,len(assets))
                                                            message += '\n\n'
                                                            for asset in assets:
                                                                ipAddress = asset['address']
                                                                hostName = asset['dnsName']
                                                                systemName = asset['assetName']
                                                                tagList = set()
                                                                for tagListEntry in asset['tagList']:
                                                                    for tag in asset['tagList'][tagListEntry]:
                                                                        tagName = tag['tagName']
                                                                        if not 'Cloud Agent' in tagName and not 'ScanTime' in tagName:
                                                                            tagList.add(tag['tagName'])
                                                                tags = ','.join(sorted(tagList))
                                                                for software in asset['softwareListData']['software']:
                                                                    product = software['discoveredName'].lower().title()
                                                                    version = software['version'] if software['version'] else "Unknown"
                                                                    if query.lower() in product.lower():
                                                                        csvFile += f'"{ipAddress}","{hostName}","{systemName}","{product}","{version}","{tags}"\n'
                                                                        if product not in productlist:
                                                                            productlist[product] = {}
                                                                        if version not in productlist[product]:
                                                                            productlist[product][version] = 0
                                                                        productlist[product][version] += 1
                                                            message += '\n| Product | Version | Count |'
                                                            message += '\n| :- | -: | -: |'
                                                            for product in sorted(productlist):
                                                                for version in {k: v for k,v in sorted(productlist[product].items(), key=lambda _: _[1], reverse=True)}:
                                                                    message += f'\n| {product} | {version} | {productlist[product][version]} |'
                                                            message += '\n\n'
                                                            messages.append({'text': message})
                                                            messages.append({'text': 'CSV of Qualys results:', 'uploads': [
                                                                                {'filename': 'qualys-'+querytype+'-'+query+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.csv', 'bytes': csvFile.encode('utf-8')}
                                                                            ]})
                                                        else:
                                                            messages.append({'text': 'No Qualys assets were found matching the given fields/values.'})
                                            if querytype in ('ip', 'host'):
                                                if 'assetListData' in json_response:
                                                    assetListData = json_response['assetListData']
                                                    if 'asset' in assetListData:
                                                        assets = assetListData['asset']
                                                        if len(assets):
                                                            headercount = 0
                                                            message = '\n**Qualys CSAM query results**'
                                                            message += '\n*Querytype*: `%s` --- *Query*: `%s`' % (querytype,query)
                                                            message += '\n\n'
                                                            foundfields = set()
                                                            for asset in assets:
                                                                for displayfield in displayfields:
                                                                    if displayfield in asset:
                                                                        message += f'| {displayfields[displayfield]} '
                                                                        foundfields.add(displayfield)
                                                                        headercount += 1
                                                            message += ' |\n' + ('| :- ' * headercount) + ' |\n'
                                                            for asset in assets:
                                                                for displayfield in displayfields:
                                                                    if displayfield in foundfields:
                                                                        if displayfield in ('assetName', 'dnsName', 'sensorLastUpdatedDate'):
                                                                            message += f'| `{asset[displayfield]}` '
                                                                        if displayfield == 'hardware':
                                                                            hwtype = asset[displayfield]['category2']
                                                                            product = asset[displayfield]['manufacturer']
                                                                            message += f'| `{hwtype}` (`{product}`)'
                                                                        if displayfield == 'address':
                                                                            addresses = set()
                                                                            addresses.add(asset[displayfield])
                                                                            if 'networkInterfaceListData' in asset:
                                                                                networkInterfaceListData = asset['networkInterfaceListData']
                                                                                if 'networkInterface' in networkInterfaceListData:
                                                                                    networkInterfaces = networkInterfaceListData['networkInterface']
                                                                                    for networkInterface in networkInterfaces:
                                                                                        if networkInterface['addressIpV4']:
                                                                                            addresses.add(networkInterface['addressIpV4'])
                                                                                        if networkInterface['addressIpV6']:
                                                                                            addresses.add(networkInterface['addressIpV6'])
                                                                                message += '| `%s` ' % ('`, `'.join(addresses),)
                                                                        if displayfield == 'operatingSystem':
                                                                            osName = asset[displayfield]['osName']
                                                                            message += f'| `{osName}`'
                                                                        if displayfield == 'openPortListData':
                                                                            services = collections.OrderedDict()
                                                                            if 'openPortListData' in asset:
                                                                                openPortListData = asset['openPortListData']
                                                                                if 'openPort' in openPortListData:
                                                                                    openPorts = openPortListData['openPort']
                                                                                    for openPort in openPorts:
                                                                                        port = openPort['port']
                                                                                        protocol = openPort['protocol']
                                                                                        service = openPort['detectedService']
                                                                                        services[str(port)+'/'+protocol] = service
                                                                                message += '| '
                                                                                for service in sorted(services):
                                                                                    message += f'`{service}`:`{services[service]}`, '
                                                                            message = message[:-1]
                                                                        if displayfield == 'tagList':
                                                                            assettags = set()
                                                                            if 'tagList' in asset:
                                                                                tagList = asset['tagList']
                                                                                if 'tag' in tagList:
                                                                                    tags = tagList['tag']
                                                                                    for tag in tags:
                                                                                        assettags.add(tag['tagName'])
                                                                            message += '| `%s` ' % ('`, `'.join(assettags),)
                                                            messages.append({'text': message})
                                                        else:
                                                            messages.append({'text': 'No Qualys assets were found matching the given fields/values.'})
                                
                                        except Exception as e:
                                            messages.append({'text': 'A Python error occurred parsing the Qualys API response: `%s`\n```%s```\n' % (str(e), traceback.format_exc())})
                            else:
                                messages.append({'text': 'No Qualys assets were found matching the given fields/values.'})
                        except Exception as e:
                            messages.append({'text': 'The Qualys CSAM API call returned an unexpected result/error: `%s`\n```%s```\n```%s```\n' % (str(e), traceback.format_exc(), response.content)})
                else:
                    messages.append({'text': 'The Qualys module could not obtain a valid JWT token. Check your credentials and/or subscription permissions.'})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching the Qualys API: `%s`\n```%s```\n' % (str(e), traceback.format_exc())})
    finally:
        return {'messages': messages}

if __name__ == '__main__':
    process('command','channel','username',sys.argv[1:],'files','conn')
