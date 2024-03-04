#!/usr/bin/env python3

import base64
import json
import pypandoc
import requests
import textwrap
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


def process(command, channel, username, params, files, conn):
    try:
        subcommand = params[0]
        messages = []
        if len(params)<1:
            messages.append({'text': 'You need to specify a language from the list (`%s`) and case number, or the `upload` command with an image to convert to Base64.'} % ('`, `'.join(settings.LANGMAP,)))
        else:
            headers = {
                'Authorization': 'Bearer %s' % settings.APIURL['docgen']['token'],
                'Content-Type': settings.CONTENTTYPE,
            }
            if subcommand == "upload":
                if not len(files):
                    messages.append({'text': "No image(s) to upload were given!"})
                else:
                    pagecontent = ""
                    for file in files:
                        id = file['id']
                        imagebytes = conn.files.get_file(id).content # Grab the bytes
                        imageb64 = base64.b64encode(imagebytes).decode('utf-8')
                        imagename = file['name']
                        mime_type = file['mime_type']
                        for language in settings.LANGMAP:
                            pagecontent += '\n<!---'+language+'--->\n'
                            pagecontent += '\n<img class="%s" src="data:%s;base64,%s" alt="%s" /><br />\n' % (imagename,mime_type,imageb64,imagename)
                            pagecontent += '\n<!---'+language+'--->\n'
                        ### Now create a WikiJS page for every attached image
                        description = "%s" % (imagename,)
                        editor = "markdown"
                        isPublished = "true"
                        isPrivate = "false"
                        locale = "en"
                        path = "/home/%s" % (imagename.replace('.','-'),)
                        title = "%s" % (imagename,)
                        tags = '"'+title+'"'
                        if len(params)>1:
                            tags += ',"' + '", "'.join(params[1:]) + '"'
                        tags = "[" + tags + "]"
                        query = """
                        mutation Page {
                            pages {
                                create (
                                    content: \"\"\"%s\"\"\",
                                    description: \"\"\"%s\"\"\",
                                    editor: "%s",
                                    isPublished: %s,
                                    isPrivate: %s,
                                    locale: "%s",
                                    path: "%s",
                                    tags: %s,
                                    title: \"\"\"%s\"\"\"
                                )
                                {
                                    responseResult {
                                        succeeded,
                                        errorCode,
                                        slug,
                                        message
                                    },
                                    page {
                                        id,
                                        path,
                                        title
                                    }
                                }
                            }
                        }
                        """ % (pagecontent, description, editor, isPublished, isPrivate, locale, path, tags, title,)
                        query = json.dumps({'query': query.strip()})
                        with requests.post(settings.APIURL['docgen']['url']+'/graphql', headers=headers, data=query) as response:
                            json_response = response.json()
                            if 'data' in json_response:
                                if 'pages' in json_response['data']:
                                    if 'create' in json_response['data']['pages']:
                                        imagepath = settings.APIURL['docgen']['url'].replace('graphql','')
                                        messages.append({'text': "Image page created for ["+imagename+"]("+imagepath+path+")"})
            elif not subcommand in settings.LANGMAP:
                messages.append({'text': 'Language `%s` not recognized' % (subcommand,)})
            else:
                language = subcommand
                casenumber = params[1]
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
                                if pid.lower() == page['path'].lower().split('/').pop():
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
                        extra_args = ['--section-divs', '--number-offset=0']
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
                                if template_variable == 'reporttypename':
                                    target = '<br /><br />'.join(textwrap.wrap(template_cases[template_variable],24))
                                else:
                                    target = template_cases[template_variable]
                                html = html.replace(source,target)
                        for field in customerdata:
                            try:
                                html = html.replace('%'+field+'%',customerdata[field])
                            except:
                                messages.append({'text': "Warning: the `%s` field could not be templatized during document generation!" % (field,)})
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
                            #with open(mdfile, 'rb') as f:
                            filecontent = skeletondocument
                            filename = mdfile.replace(MODULEDIR,'')
                            if len(filecontent):
                                messages.append({
                                    'text': '**MarkDown Source Before Rendering**: `%s`' % (filename,),
                                    'uploads': [
                                        {'filename': filename, 'bytes': skeletondocument}
                                    ]
                                })
                            os.unlink(mdfile)
                            os.unlink(htmlfile)
                            os.unlink(pdffile)
                        except:
                            raise
                else:
                    messages.append({'text': 'Case `%s` does not yet exist.' % (casenumber,)})
    except Exception as e:
        messages.append({'text': 'A Python error occurred during document generation:\nError:' + str(traceback.format_exc())})
    finally:
        return {'messages': messages}
