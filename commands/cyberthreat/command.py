#!/usr/bin/env python3
import re
import requests
import tldextract
from pathlib import Path
from . import cyberthreat

try:
    from commands.cyberthreat import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings # things that doesnt work
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/cyberthreat/settings.py').is_file():
        try:
            from commands.cyberthreat import settings
        except ModuleNotFoundError: # local test run
            import settings

"""
Got some problems with the above way of importing settings. Throws an error is there is no settings module, just defaults
"""


#print(f"Locals: {locals()}")
results = cyberthreat.wget('actors')

actorlist = dict()
for actor in results['results']:
    actorlist[actor['name']]=actor


def process(command, channel, username, params, files, conn):
    filters = '&'.join(settings.APIURL['cyberthreat']['filters'])


    if len(params)>0:
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http').lower()
        intro = f"cyberthreat.nl *Hosting Intelligence* API search for `{params}`:"
        listitem = '`\n- `'
        try:

            if params in actorlist:
                print(f"Found {params} in actorlist")
                text = f"*{actorlist[params]['name'].capitalize()}*\n{actorlist[params]['description']}"

            elif re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", params):
                results = cyberthreat.wget('addresses/'+params+'?'+filters)
                print(f"Results: {results}")
                for address in results:
                    text=f"IP address {params} {settings.confidence_tabel[address['credibility']]['level']} used by the actor **{address['actor'].capitalize()}**. "

            elif params:
                print('domain')
                extract = tldextract.extract(params)
                extracted_domain = extract.registered_domain
                if extracted_domain:
                    results = cyberthreat.wget('domains?domain='+extracted_domain+'&'+filters)
                    results = results.get('results')
                    print(f"Results: {results}")
                    fqdnlist = dict()
                    
                    """
                    resufle the list so we can work with it as we want.
                    """
                    for result in results:
                        domain = result['domain']
                        fqdn   = result['fqdn']
                        if not domain in fqdnlist:
                            fqdnlist[domain]={'subdomains': set()}
                        if not fqdn==domain:
                            fqdnlist[domain]['subdomains'].add(fqdn)

                        fqdnlist[domain]['credibility']=min(fqdnlist[domain].get('credibility',10), result['credibility'])
                        fqdnlist[domain]['actor'] = result.get('actor')
                        fqdnlist[domain]['type']  = result.get('type')
                    
                    if len(fqdnlist):
                        text='The domainname '

                    """
                    There should have been only one domain returned, but for robustness we do a for loop.
                    """
                    for domain in fqdnlist:
                        text+=f"_{domain}_ {settings.confidence_tabel[fqdnlist[domain]['credibility']]['level']} hosted on the {fqdnlist[domain]['type']} network of actor **{fqdnlist[domain]['actor'].capitalize()}**.\n"
                        if len(fqdnlist[domain]['subdomains']):
                            text+=f"We have found the following subdomains: \n- `{listitem.join(fqdnlist[domain]['subdomains'])}`."
                        
                else:
                    """ In case the params doesnt even look like a valid domain name. """
                    print('nothing to check')
                    return

            if 'text' in locals():
                return {'messages': [
                    {'text': intro + '\n' + text},
                ]}
            #else:
            #    return {'messages': [
            #        {'text': 'cyberthreat API searched for `%s` without result' % (params.strip(),)}
            #    ]}
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred searching cyberthreat for `%s`:\nError: `%s`' % (params, e)},
            ]}
