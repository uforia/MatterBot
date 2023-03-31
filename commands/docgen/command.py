#!/usr/bin/env python3

import datetime
import requests
from pathlib import Path
try:
    from commands.docgen import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/docgen/settings.py').is_file():
        try:
            from commands.docgen import settings
        except ModuleNotFoundError: # local test run
            import settings


def process(command, channel, username, params):
    querytypes = settings.DOCTYPES
    typemap = settings.TYPEMAP
    if len(params)>0:
        messages = []
        try:
            if len(params)<2:
                messages.append({'text': 'You need to specify the relevant name and IDs, separated by comma\'s!'})
            else:
                querytype = params[0].lower()
                nameid = params[1]
                if not querytype in querytypes:
                    messages.append({'text': 'You need to specify at least a valid document type: `%s`!' % (querytypes,)})
                else:
                    auth = {
                        'Authorization': 'Bearer %s' % settings.APIURL['docgen']['token'],
                        'Content-Type': settings.CONTENTTYPE,
                    }
                    skeletondocument = []
                    for pid in params[2:]:
                        pages = '{"query":"query { pages { list (orderBy: PATH) { id path title }}}"}'
                        with requests.post(settings.APIURL['docgen']['url'], headers=auth, data=pages) as response:
                            pages = response.json()
                        if 'data' in pages:
                            for page in pages['data']['pages']['list']:
                                if pid in page['path'].lower():
                                    pagecontent = '{"query":"query { pages { single (id: %d) { content }}}"}' % (page['id'],)
                                    with requests.post(settings.APIURL['docgen']['url'], headers=auth, data=pagecontent) as response:
                                        pagecontent = response.json()
                                        if 'data' in pagecontent:
                                            content = pagecontent['data']['pages']['single']['content']
                                        skeletondocument.append(content)
                    if len(skeletondocument):
                        now = datetime.datetime.now().strftime('%Y%m%d')
                        doctype = typemap[querytype]
                        # To-Do: needs database of customer info
                        nameid = nameid
                        filename = now+'-'+doctype+'-'+nameid+'.md'
                        messages.append({'text': doctype+' for '+nameid+' at '+now+':' ,'uploads': [
                            {'filename': filename, 'bytes': ''.join(skeletondocument).encode('utf-8')}
                        ]})
        except Exception as e:
            messages.append({'text': "An error occurred retrieving WikiJS content for `%s`:\nError: `%s`" % (params, str(e))})
        finally:
            return {'messages': messages}