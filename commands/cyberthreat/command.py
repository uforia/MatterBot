#!/usr/bin/env python3
import re
import tldextract
from datetime import datetime

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

from . import cyberthreat
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
                text = f"**{actorlist[params]['name'].capitalize()}**\n{actorlist[params]['description']}"

            elif re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-65535]*)?$", params):
                results = cyberthreat.wget('addresses/'+params+'?'+filters)
                for address in results:
                    last_seen = datetime.strptime(address['last_seen'], '%Y-%m-%dT%H:%M:%S.%f%z')
                    text=f"IPv4 address `{params}` {settings.confidence_tabel[address['credibility']]['level']} used by the actor **{address['actor'].capitalize()}**.\n"
                    text+=f"Last seen: {last_seen.strftime('%Y-%m-%d')}"
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
                    
                    if len(fqdnlist):
                        text='The domainname '

                        """
                        There should have been only one domain returned, but for robustness we do a for loop.
                        """
                        for domain in fqdnlist:
                            text+=f"`{domain}` {settings.confidence_tabel[fqdnlist[domain]['credibility']]['level']} hosted on the {fqdnlist[domain]['type']} network of actor **{fqdnlist[domain]['actor'].capitalize()}**.\n"
                            text+=f"Last seen: {fqdnlist[domain]['last_seen'].strftime('%Y-%m-%d')}.\n"
                            if len(fqdnlist[domain]['subdomains']):
                                text+=f"We have found the following subdomains: \n- `{listitem.join(fqdnlist[domain]['subdomains'])}`."
                else:
                    """ In case the params doesnt even look like a valid domain name. """
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
