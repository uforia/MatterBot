#!/usr/bin/env python3

# Note: this module assumes you're using a Microsoft Azure Search index (https://...search.windows.net)

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
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
