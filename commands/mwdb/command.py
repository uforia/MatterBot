#!/usr/bin/env python3

import collections
import mwdblib
import re
import requests
import traceback
from pathlib import Path
try:
    from commands.mwdb import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/mwdb/settings.py').is_file():
        try:
            from commands.mwdb import settings
        except ModuleNotFoundError: # local test run
            import settings

headers = {
    'Authorization': f'Bearer {settings.APIURL['mwdb']['key']}',
}
filefields = collections.OrderedDict({
    'file_name': {
        'name': 'Filename',
        'align': ':-',
    },
    'file_size': {
        'name': 'Size',
        'align': ':-',
    },
    'file_type': {
        'name': 'Filetype',
        'align': ':-',
    },
    'upload_time': {
        'name': 'Submitted',
        'align': ':-',
    },
    'tags': {
        'name': 'Tags',
        'align': ':-',
    },
    'md5': {
        'name': 'MD5',
        'align': ':-',
    },
    'sha1': {
        'name': 'SHA1',
        'align': ':-',
    },
    'sha256': {
        'name': 'SHA256',
        'align': ':-',
    },
    'ssdeep': {
        'name': 'SSDEEP',
        'align': ':-',
    },
})
blobfields = collections.OrderedDict({
    'blob_name': {
        'name': 'Name',
        'align': ':-',
    },
    'blob_type': {
        'name': 'Type',
        'align': ':-',
    },
    'blob_size': {
        'name': 'Size',
        'align': ':-',
    },
    'upload_time': {
        'name': 'Submitted',
        'align': ':-',
    },
    'tags': {
        'name': 'Tags',
        'align': ':-',
    },
    'parents': {
        'name': 'Parents',
        'align': ':-',
    }
})
configfields = collections.OrderedDict({
    'config_type': {
        'name': 'Type',
        'align': ':-',
    },
    'family': {
        'name': 'Malware Family',
        'align': ':-',
    },
    'upload_time': {
        'name': 'Submitted',
        'align': ':-',
    },
    'tags': {
        'name': 'Tags',
        'align': ':-',
    },
    'parents': {
        'name': 'Parents',
        'align': ':-',
    }
})

def checkHash(value):
    return True if re.search(r"^[A-Fa-f0-9]{32}$", value) or\
       re.search(r"^[A-Fa-f0-9]{40}$", value) or\
       re.search(r"^[A-Fa-f0-9]{64}$", value) or\
       re.search(r"((\d*):(\w*):(\w*)|(\d*):(\w*)\+(\w*):(\w*))", value) else False

def getBlobParents(id, mwdb):
    try:
        result = mwdb.query(f'{id}')
        if blob := result.data:
            return blob['parents']
    except:
        pass
    return None

def getConfigs(values, mwdb):
    configs = []
    for value in values:
        try:
            result = mwdb.query(f'{value}')
            if config := result.data:
                configs.append(config)
        except:
            pass
    return configs if len(configs) else None

def getDownloads(ids):
    downloads = []
    for id in ids:
        url = settings.APIURL['mwdb']['url']+f'file/{id}/download/zip'
        try:
            with requests.get(url, headers=headers) as response:
                if response.status_code == 404:
                    return None
                if response.status_code == 200:
                    filename = 'mwdb-'+id+'.zip'
                    content = response.content
                    downloads.append({'filename': filename, 'bytes': content})
        except:
            pass
    return downloads if len(downloads) else None

def getFiles(ids, mwdb):
    files = []
    for id in ids:
        try:
            data = mwdb.query_file(f'{id}').data
            files.append(data)
        except:
            pass
    return files if len(files) else None

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        querytypes = ('blob', 'hash')
        querytype = params[0]
        query = [_.replace('[', '').replace(']', '') for _ in params[1:]]
        try:
            messages = []
            if not querytype in querytypes:
                if len(query) == 0:
                    query = [querytype]
                    if checkHash(querytype):
                        querytype = 'hash'
                    else:
                        querytype = 'multi'
                elif len(query) >= 1:
                    query.insert(0,querytype)
                    querytype = 'multi'
            else:
                if len(query) == 0:
                    messages.append({'text': f'MWDB Error: please specify what `{querytype}` to search for!'})
                if len(query) > 1:
                    querytype = 'multi'
            if not settings.APIURL['mwdb']['key']:
                messages.append({'text': 'Error: the MWDB module requires a valid API key.'})
            else:
                files = []
                blobs = []
                configs = []
                downloads = []
                query = ' '.join(query)
                mwdb = mwdblib.MWDB(api_url=settings.APIURL['mwdb']['url'], api_key=settings.APIURL['mwdb']['key'])
                if querytype == 'hash':
                    hash = query
                    try:
                        result = mwdb.query(f'{hash}')
                    except (mwdblib.exc.ObjectNotFoundError, mwdblib.exc.EndpointNotFoundError):
                        pass
                    if result:
                        if 'type' in result.data:
                            if result.data['type'] == 'file':
                                if fileresults := getFiles([hash], mwdb):
                                    files += fileresults
                                if downloadresults := getDownloads([hash]):
                                    downloads += downloadresults
                            if 'config' in result.data['type']:
                                if configresults := getConfigs([hash], mwdb):
                                    configs += configresults
                if querytype == 'multi':
                    url = settings.APIURL['mwdb']['url']+f'blob?query=multi:{query}'
                    try:
                        with requests.get(url, headers=headers) as response:
                            json_response = response.json()
                            if 'blobs' in json_response:
                                if len(json_response['blobs']):
                                    blobs += json_response['blobs']
                                    for blob in blobs:
                                        blob['parents'] = getBlobParents(blob['id'], mwdb)
                    except:
                        raise
                for file in files:
                    message = f'**MWDB Files** `{querytype}`:`{file['id']}`\n\n'
                    for filefield in filefields:
                        if filefield in file:
                            message += f'| **{filefields[filefield]['name']}** '
                    message += '|\n'
                    for filefield in filefields:
                        if filefield in file:
                            message += f'| {filefields[filefield]['align']} '
                    message += '|\n'
                    for filefield in filefields:
                        if filefield in file:
                            value = file[filefield]
                            if isinstance(value,int):
                                value = str(value)
                            elif isinstance(value,list):
                                if len(value):
                                    value = '`, `'.join([''.join([_ for _ in _.values()]) for _ in value])
                                else:
                                    value = '-'
                            elif not len(value):
                                value = '-'
                            message += f'| `{value}` '
                    message += '|\n'
                    message += '\n\n'
                    messages.append({'text': message})
                if len(configs):
                    message = f'**MWDB Configs** `{querytype}`:`{query}`\n\n'
                    for configfield in configfields:
                        if configfield in configs[0]:
                            message += f'| **{configfields[configfield]['name']}** '
                    message += '|\n'
                    for configfield in configfields:
                        if configfield in configs[0]:
                            message += f'| {configfields[configfield]['align']} '
                    message += '|\n'
                    for config in configs:
                        for configfield in configfields:
                            if configfield in config:
                                value = config[configfield]
                                if isinstance(value,int):
                                    value = str(value)
                                elif isinstance(value,list):
                                    if configfield == 'parents':
                                        parents = []
                                        for parent in value:
                                            parents.append(parent['id'])
                                        value = '`, `'.join(parents)
                                    elif configfield == 'tags':
                                        tags = []
                                        for parenttags in config['parents']:
                                            for parenttag in parenttags['tags']:
                                                tags += [parenttag['tag']]
                                        value = '`, `'.join(tags)
                                    elif len(value):
                                        value = '`, `'.join([''.join([_ for _ in _.values()]) for _ in value])
                                    else:
                                        value = '-'
                                elif not len(value):
                                    value = '-'
                                message += f'| `{value}` '
                    message += '|\n'
                    message += '\n\n'
                    messages.append({'text': message})
                if len(blobs):
                    message = f'**MWDB Configs** `{querytype}`:`{query}`\n\n'
                    for blobfield in blobfields:
                        message += f'| **{blobfields[blobfield]['name']}** '
                    message += '|\n'
                    for blobfield in blobfields:
                        message += f'| {blobfields[blobfield]['align']} '
                    message += '|\n'
                    for blob in blobs:
                        for blobfield in blobfields:
                            value = blob[blobfield]
                            if isinstance(value,int):
                                value = str(value)
                            elif isinstance(value,list):
                                if blobfield == 'parents':
                                    parents = []
                                    for parent in value:
                                        tags = [_['tag'] for _ in parent['tags']]
                                        if len(tags):
                                            parents.append(parent['id']+'`:`'+'`, `'.join(tags))
                                        else:
                                            parents.append(parent['id'])
                                    value = '`, `'.join(parents)
                                elif len(value):
                                    value = '`, `'.join([''.join([_ for _ in _.values()]) for _ in value])
                                else:
                                    value = '-'
                            elif not len(value):
                                value = '-'
                            message += f'| `{value}` '
                        message += '|\n'
                    message += '\n\n'
                    messages.append({'text': message})
                if len(downloads):
                    messages.append({'text': f'**MWDB**: *Sample download(s)*', 'uploads': downloads})
        except Exception as e:
            messages.append({'text': 'A Python error occurred searching the MWDB API: `%s`\n```%s```\n' % (str(e), traceback.format_exc())})
        finally:
            return {'messages': messages}