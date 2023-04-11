#!/usr/bin/env python3

import csv
import datetime
import requests
import sys
from io import StringIO
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
    if len(params)>0:
        messages = []
        try:
            if len(params)<2:
                messages.append({'text': 'You need to specify the relevant ID and language!'})
            else:
                headers = {
                    'Authorization': 'Bearer %s' % settings.APIURL['docgen']['token'],
                    'Content-Type': settings.CONTENTTYPE,
                }
                casenummer = params[0].lower().strip()
                language = params[1].lower().strip()
                query = '{"query":"query { pages { list (orderBy: PATH) { id path title }}}"}'
                with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=query) as response:
                    pages = response.json()
                    if 'data' in pages:
                        for page in pages['data']['pages']['list']:
                            if page['title'].lower() == settings.TEMPLATEVARS.lower():
                                query = '{"query":"query { pages { single (id: %d) { content }}}"}' % (page['id'],)
                                with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=query) as response:
                                    pagecontent = response.json()
                                    if 'data' in pagecontent:
                                        template_variables_content = csv.DictReader(StringIO(pagecontent['data']['pages']['single']['content']))
                            if page['title'].lower() == settings.TEMPLATEIDCHAIN.lower():
                                query = '{"query":"query { pages { single (id: %d) { content }}}"}' % (page['id'],)
                                with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=query) as response:
                                    pagecontent = response.json()
                                    if 'data' in pagecontent:
                                        template_id_chain_content = csv.DictReader(StringIO(pagecontent['data']['pages']['single']['content']))
                template_variables = None
                if template_variables_content and template_id_chain_content:
                    for entry in template_variables_content:
                        if entry['casenummer'].lower() == casenummer.lower():
                            template_variables = entry 
                template_id_chain = None
                if template_variables:
                    if 'type' in template_variables:
                        for entry in template_id_chain_content:
                            if entry['type'] == template_variables['type']:
                                template_id_chain = entry
                if template_id_chain:
                    template_variables['datum'] = datetime.datetime.now().strftime('%Y%m%d')
                    template_variables['reporttypename'] = template_id_chain['reporttypename']
                    skeletondocument = []
                    for pid in template_id_chain['ids'].split(' '):
                        pages = '{"query":"query { pages { list (orderBy: PATH) { id path title }}}"}'
                        with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=pages) as response:
                            pages = response.json()
                        if 'data' in pages:
                            for page in pages['data']['pages']['list']:
                                if pid in page['path'].lower():
                                    pagecontent = '{"query":"query { pages { single (id: %d) { content }}}"}' % (page['id'],)
                                    with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=pagecontent) as response:
                                        pagecontent = response.json()
                                        if 'data' in pagecontent:
                                            content = pagecontent['data']['pages']['single']['content'].split('---')
                                            if language.lower() in ('english', 'en'):
                                                content = content[0]
                                            if language.lower() in ('nederlands', 'nl'):
                                                content = content[1]
                                        skeletondocument.append(content)
                    skeletondocument = ''.join(skeletondocument).encode('utf-8')
                    for template_variable in template_variables:
                        source = b'%'+bytes(template_variable.encode('utf-8'))+b'%'
                        target = bytes(template_variables[template_variable].encode('utf-8'))
                        skeletondocument = skeletondocument.replace(source,target)
                    if len(skeletondocument):
                        doctype = template_variables['reporttypename']
                        # To-Do: needs database of customer info
                        now = template_variables['datum']
                        nameid = casenummer
                        filename = now+'-'+doctype+'-'+nameid+'.md'.replace(' ','_')
                        messages.append({'text': doctype+' for '+nameid+' at '+now+':' ,'uploads': [
                            {'filename': filename, 'bytes': skeletondocument}
                        ]})
                else:
                    messages.append({'text': 'Document type `%s` is not implemented yet.' % (template_variables['type'],)})
        except Exception as e:
            messages.append({'text': "An error occurred retrieving WikiJS content for `%s`:\nError: `%s`" % (params, str(e))})
        finally:
            return {'messages': messages}