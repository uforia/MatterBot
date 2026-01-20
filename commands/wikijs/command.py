#!/usr/bin/env python3

# Note: this module assumes you're using a Microsoft Azure Search index (https://...search.windows.net)

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

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

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        credential = AzureKeyCredential(settings.APIKEY)
        client = SearchClient(endpoint=settings.APIENDPOINT,
                              index_name=settings.INDEX,
                              credential=credential)
        query = ' '.join(params).replace('[.]','.')
        results = client.search(search_text=query)
        answers = []
        for result in results:
            title = result['title']
            description = result['description']
            content = result['content']
            url = settings.WIKIURL + '/' + result['path']
            if all(param in content for param in params):
                answers.append('[' + description + '](' + url + ')')
        message = 'Search term `' + ' AND '.join(params) + '` was found in:\n'
        message += '\n'.join(answers)
        if len(answers)>0:
            return {'messages': [
                {'text': message.strip()},
            ]}
        else:
            return {'messages': [
                {'text': 'WikiJS search for `%s` returned no results.' % (' '.join(params),)},
            ]}
    else:
        return {'messages': [
            {'text': 'At least search for something, %s!' % (username,)}
        ]}
