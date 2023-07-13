#!/usr/bin/env python3

import csv
import datetime
import requests
import sys
import traceback
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
    try:
        messages = []
        if len(params)<3:
            messages.append({'text': 'You need to specify the relevant language, type and customer ID!'})
        else:
            headers = {
                'Authorization': 'Bearer %s' % settings.APIURL['docgen']['token'],
                'Content-Type': settings.CONTENTTYPE,
            }
            language = params[0]
            if not language in settings.LANGMAP:
                messages.append({'text': 'Language `%s` not recognized' % (language,)})
            else:
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
                                        template_idchain_content = csv.DictReader(StringIO(pagecontent['data']['pages']['single']['content']))
                            if page['title'].lower() == settings.TEMPLATECUSTOMERS.lower():
                                query = '{"query":"query { pages { single (id: %d) { content }}}"}' % (page['id'],)
                                with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=query) as response:
                                    pagecontent = response.json()
                                    if 'data' in pagecontent:
                                        template_customers_content = csv.DictReader(StringIO(pagecontent['data']['pages']['single']['content']))
                print(template_idchain_content)
                print(template_customers_content)
                print(template_variables_content)
                """
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
                """
    except Exception as e:
        print(traceback.format_exc())
        messages.append({'text': 'A Python error occurred during document generation:\nError:' + str(e)})
    finally:
        return {'messages': messages}