#!/usr/bin/env python3

# Note: this module assumes you're using a Microsoft Azure Search index (https://...search.windows.net)

import aiohttp
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from pathlib import Path
try:
    from commands.wikijs import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/wikijs/settings.py').is_file():
        try:
            from commands.wikijs import settings
        except ModuleNotFoundError: # local test run
            import settings

async def process(connection, channel, username, params):
    if len(params)>0:
        credential = AzureKeyCredential(settings.APIKEY)
        client = SearchClient(endpoint=settings.APIENDPOINT,
                              index_name=settings.INDEX,
                              credential=credential)
        query = ' '.join(params)
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
                {'text': 'WikiJS search for `%s` returned no results.' % (params,)},
            ]}
    else:
        return {'messages': [
            {'text': 'At least search for something, %s!' % (username,)}
        ]}
