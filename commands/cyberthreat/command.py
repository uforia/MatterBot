#!/usr/bin/env python3
import re
import logging
import tldextract
from pathlib import Path
from datetime import datetime
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

"""
Input data in the format

{
    "source":"provider",
    "responses": [
        {
            "paragraph":"subtitle",
            "preamble":"introduction to source",
            "data": [
                {"category":"category", "datapoint":"datapoint", "stixtype":"ipv4-addr", "value":"value"},
                {"category":"category", "datapoint":"datapoint", "value":"value"}
            ]
        }
    ]
}

Converts to a message text and possibly an attachment.
The text can have multiple paragraph with a short introduction

"""




def process(command, channel, username, params, files, conn):
    filters = '&'.join(settings.APIURL['cyberthreat']['filters'])


    if len(params)>0:
        params = params[0].replace('[', '').replace(']', '').replace('hxxp','http').lower().strip()
        data = { "source":"cyberthreat hosting intelligence",
                    "responses": []
}
        
        data['intro'] = f"cyberthreat.nl *Hosting Intelligence* API search for `{params}`:"
        listitem = '`\n- `'
        try:
            if params in actorlist:
                text = f"**{actorlist[params]['name'].capitalize()}**\n{actorlist[params]['description']}"
                data['responses'].append({})
                data['responses'][0]['paragraph'] = "Bulletproof hosting provider"
                data['responses'][0]['preamble']  = actorlist[params]['description']
                data['responses'][0]['data'] = list()
                data['responses'][0]['data'].append({"category":"Actor", "datapoint":"name", "stixtype":"", "value":actorlist[params]['name']})
                data['responses'][0]['data'].append({"category":"Actor", "datapoint":"type", "stixtype":"", "value":actorlist[params]['type']})


            elif re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", params):
                results = cyberthreat.wget('addresses/'+params+'?'+filters)
                for address in results:
                    last_seen = datetime.strptime(address['last_seen'], '%Y-%m-%dT%H:%M:%S.%f%z')
                    data['responses'].append(dict())
                    data['responses'][0]['paragraph'] = "IP Lookup"
                    data['responses'][0]['preamble']=f"IPv4 address `{params}` {settings.confidence_tabel[address['credibility']]['level']} used by the actor **{address['actor'].capitalize()}**.\n"
                    data['responses'][0]['data'] = list()
                    data['responses'][0]['data'].append({"category":"Indicator", "datapoint":"ipv4 address", "stixtype":"ipv4-addr", "value":params})
                    data['responses'][0]['data'].append({"category":"Indicator", "datapoint":"last seen", "stixtype":"", "value":last_seen.strftime('%Y-%m-%d')})
                    data['responses'][0]['data'].append({"category":"Indicator", "datapoint":"actor", "stixtype":"", "value":address['actor'].capitalize() })
                    data['responses'][0]['data'].append({"category":"Indicator", "datapoint":"actor type", "stixtype":"", "value":address['type'].capitalize() })
                    data['responses'][0]['data'].append({"category":"Indicator", "datapoint":"credibility", "stixtype":"", "value": settings.confidence_tabel[address['credibility']]['short_description']})

            
            elif params:
                extract = tldextract.extract(params)
                extracted_domain = extract.registered_domain
                if extracted_domain:
                    results = cyberthreat.wget('domains?domain='+extracted_domain+'&'+filters)
                    results = results.get('results')
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
                        last_seen = datetime.strptime(result['last_seen'], '%Y-%m-%dT%H:%M:%S.%f%z')
                        fqdnlist[domain]['credibility']=min(fqdnlist[domain].get('credibility',10), result['credibility'])
                        fqdnlist[domain]['last_seen']=max(fqdnlist[domain].get('last_seen', last_seen), last_seen)
                        fqdnlist[domain]['actor'] = result.get('actor')
                        fqdnlist[domain]['type']  = result.get('type')
                    
                    logging.warning(f"fqdn list: {fqdnlist}")
                    if len(fqdnlist):
                        text='The domainname '

                        """
                        There should have been only one domain returned, but for robustness we do a for loop.
                        """
                        for domain in fqdnlist:
                            text+=f"`{domain}` {settings.confidence_tabel[fqdnlist[domain]['credibility']]['level']} hosted on the {fqdnlist[domain]['type']} network of actor **{fqdnlist[domain]['actor'].capitalize()}**.\n"

                            data['responses'].append({})
                            data['responses'][0]['paragraph'] = "Domain search"
                            data['responses'][0]['preamble']  = text
                            data['responses'][0]['data'] = list()
                            data['responses'][0]['data'].append({"category":"Hosting", "datapoint":"domain", "stixtype":"", "value":domain})
                            data['responses'][0]['data'].append({"category":"Hosting", "datapoint":"actor", "stixtype":"", "value":fqdnlist[domain]['actor']})
                            data['responses'][0]['data'].append({"category":"Hosting", "datapoint":"credibility", "stixtype":"", "value":settings.confidence_tabel[fqdnlist[domain]['credibility']]['short_description']})
                            data['responses'][0]['data'].append({"category":"Hosting", "datapoint":"last seen", "stixtype":"", "value":fqdnlist[domain]['last_seen'].strftime('%Y-%m-%d')})
                            for item in fqdnlist[domain]['subdomains']:
                                data['responses'][0]['data'].append({"category":"Domain", "datapoint":"fqdn", "stixtype":"", "value":item})
                return data
            
            else:
               return {'messages': [
                   {'text': 'cyberthreat API searched for `%s` without result' % (params.strip(),)}
               ]}
        except Exception as e:
            raise e
            return {'messages': [
                {'text': 'An error occurred searching cyberthreat for `%s`:\nError: `%s`' % (params, e)},
            ]}
            
