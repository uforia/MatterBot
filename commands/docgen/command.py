#!/usr/bin/env python3

import csv
import datetime
import os
import pypandoc
import re
import requests
import sys
import traceback
import weasyprint
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
        if len(params)<2:
            messages.append({'text': 'You need to specify the relevant language and case number!'})
        else:
            headers = {
                'Authorization': 'Bearer %s' % settings.APIURL['docgen']['token'],
                'Content-Type': settings.CONTENTTYPE,
            }
            language = params[0]
            casenumber = params[1]
            if not language in settings.LANGMAP:
                messages.append({'text': 'Language `%s` not recognized' % (language,)})
            else:
                query = '{"query":"query { pages { list (orderBy: PATH) { id path title }}}"}'
                with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=query) as response:
                    pages = response.json()
                    if 'data' in pages:
                        for page in pages['data']['pages']['list']:
                            if page['title'].lower() == settings.TEMPLATECASES.lower():
                                query = '{"query":"query { pages { single (id: %d) { content }}}"}' % (page['id'],)
                                with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=query) as response:
                                    pagecontent = response.json()
                                    if 'data' in pagecontent:
                                        template_cases_content = csv.DictReader(StringIO(pagecontent['data']['pages']['single']['content']))
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
                template_cases = None
                if template_cases_content and template_idchain_content:
                    for entry in template_cases_content:
                        if entry['casenumber'].lower() == casenumber.lower():
                            template_cases = entry 
                template_id_chain = None
                if template_cases:
                    if 'type' in template_cases:
                        for entry in template_idchain_content:
                            if entry['type'] == template_cases['type']:
                                template_id_chain = entry
                if template_id_chain:
                    template_cases['currentdate'] = datetime.datetime.now().strftime('%Y%m%d')
                    template_cases['reporttypename'] = template_id_chain['reporttypename']
                    skeletondocument = []
                    for pid in template_id_chain['ids'].split(' '):
                        pages = '{"query":"query { pages { list (orderBy: PATH) { id path title }}}"}'
                        with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=pages) as response:
                            pages = response.json()
                        if 'data' in pages:
                            for page in pages['data']['pages']['list']:
                                if pid.lower() == page['path'].lower():
                                    pagecontent = '{"query":"query { pages { single (id: %d) { content }}}"}' % (page['id'],)
                                    with requests.post(settings.APIURL['docgen']['url'], headers=headers, data=pagecontent) as response:
                                        pagecontent = response.json()
                                        if 'data' in pagecontent:
                                            langsplit = '<!---'+language+'--->'
                                            content = pagecontent['data']['pages']['single']['content'].split(langsplit)[1]
                                        if 'Report_Cover' in page['path']:
                                            coverpage = content
                                        else:
                                            skeletondocument += content
                    skeletondocument = ''.join(skeletondocument).encode('utf-8')
                    for template_variable in template_cases:
                        source = b'%'+bytes(template_variable.encode('utf-8'))+b'%'
                        target = bytes(template_cases[template_variable].encode('utf-8'))
                        skeletondocument = skeletondocument.replace(source,target)
                        if template_variable == 'customerid':
                            customerid = template_cases[template_variable]
                            for template_customer_entry in template_customers_content:
                                if template_customer_entry['customerid'] == customerid:
                                    customerdata = {}
                                    for template_customer_variable in template_customer_entry:
                                        source = template_customer_variable
                                        target = template_customer_entry[template_customer_variable]
                                        customerdata[source] = target
                    if len(skeletondocument):
                        doctype = template_cases['reporttypename'].replace(' ','_')
                        # To-Do: needs database of customer info
                        now = template_cases['currentdate']
                        nameid = customerdata['customername'].replace(' ','_')
                        MODULEDIR = "commands/docgen/"
                        templatefiles = {}
                        mdfile = MODULEDIR+now+'-'+doctype+'-'+nameid+'.md'.replace(' ','_')
                        htmlfile = MODULEDIR+now+'-'+doctype+'-'+nameid+'.html'.replace(' ','_')
                        pdffile = MODULEDIR+now+'-'+doctype+'-'+nameid+'.pdf'.replace(' ','_')
                        for templatefile in settings.LANGMAP[language]:
                            with open(MODULEDIR+settings.LANGMAP[language][templatefile],'r') as f:
                                templatefiles[templatefile] = f.read()
                        format = 'markdown'
                        extra_args = ['--section-divs', '--number-offset=1']
                        html = templatefiles['header']+pypandoc.convert_text(skeletondocument, 'html', format=format, extra_args=extra_args)+templatefiles['footer']
                        for template_variable in templatefiles:
                            source = '%'+template_variable+'%'
                            target = templatefiles[template_variable]
                            html = html.replace(source,target)
                        html = html.replace('</section>','')
                        if '%coverpage%' in html:
                            html = html.replace('%coverpage%',coverpage)
                            for template_variable in template_cases:
                                source = '%'+template_variable+'%'
                                target = template_cases[template_variable]
                                html = html.replace(source,target)
                        for field in customerdata:
                            html = html.replace('%'+field+'%',customerdata[field])
                        if '%TOCMARKER%' in html:
                            toc = ''
                            sections = re.findall(r'<section id=[^>]+>',html,re.DOTALL)
                            for section in sections:
                                html = re.sub('</h1>(?!</section>)','</h1></section>',html,flags=re.DOTALL)
                                html = re.sub('</h2>(?!</section>)','</h2></section>',html,flags=re.DOTALL)
                                html = re.sub('</h3>(?!</section>)','</h3></section>',html,flags=re.DOTALL)
                                html = re.sub('</h4>(?!</section>)','</h4></section>',html,flags=re.DOTALL)
                                html = re.sub('</h5>(?!</section>)','</h5></section>',html,flags=re.DOTALL)
                                html = re.sub('</h6>(?!</section>)','</h6></section>',html,flags=re.DOTALL)
                                m = re.search('id=\"(.+?)\"', section)
                                if m:
                                    chaptertitle = m.group(1)
                                    toc += '\n<li><a href="#'+chaptertitle+'" class="toctext"></a> <a href="'+chaptertitle+'" class="tocpagenr"> </a></li>'
                            html = html.replace('%TOCMARKER%',toc)
                        with open(mdfile, 'wb') as f:
                            f.write(content.encode())
                            f.flush()
                        with open(htmlfile, 'wb') as f:
                            f.write(html.encode())
                            f.flush()
                        html_writer = weasyprint.HTML(htmlfile)
                        css = weasyprint.CSS(filename=MODULEDIR+settings.LANGMAP[language]['css'], base_url=MODULEDIR+settings.TEMPLATEDIR)
                        html_writer.write_pdf(pdffile, stylesheets=[MODULEDIR+settings.LANGMAP[language]['css']])
                        try:
                            with open(pdffile, 'rb') as f:
                                filecontent = f.read()
                                filename = pdffile.replace(MODULEDIR,'')
                            if len(filecontent):
                                messages.append({
                                    'text': '**Document Generated Successfully**: `%s`' % (filename,),
                                    'uploads': [
                                        {'filename': filename, 'bytes': filecontent}
                                    ]
                                })
                            os.unlink(mdfile)
                            os.unlink(htmlfile)
                            os.unlink(pdffile)
                        except:
                            raise
                else:
                    messages.append({'text': 'Case type `%s` does not yet exist.' % (template_cases['type'],)})
    except Exception as e:
        messages.append({'text': 'A Python error occurred during document generation:\nError:' + str(traceback.format_exc())})
    finally:
        return {'messages': messages}