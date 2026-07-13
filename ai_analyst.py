#!/usr/bin/env python3

"""Conversational AI analyst: the command modules, used as tools by an LLM.

An analyst says `@ai we're seeing beacons to 8.8.8[.]8, thoughts?` in a channel.
This module reconstructs the case from the Mattermost thread, decides which
command modules could speak to the indicators in play, lets an LLM call them, and
writes the answer back in the thread. The thread IS the case: there is no
server-side session, so a restart loses nothing.

Three rules shape the design:

1. **The executor is the only door.** Everything the model wants to happen goes
   through AIAnalyst._run_tool_call(), which enforces the operator allow-list,
   ACLs, indicator-type acceptance, analyst authorization and call caps in code.
   Prompting is not a control. Tool results are attacker-influenceable (WHOIS
   registrant text, filenames, urlscan page content, MISP comments), so indirect
   prompt injection is in scope -- and the answer to it is that a hijacked model
   still cannot do anything but a read-only, authorized, ACL-checked, rate-capped
   lookup.

2. **Module output is redacted before it goes anywhere.** This feature is the
   first thing in MatterBot that ships module output OFF-HOST, to a third-party
   LLM endpoint. That is new exfiltration surface, and it exists for success
   output, not just for exception text -- so sanitize_tool_output() runs on every
   byte, whatever the module did. Do not delegate this to the modules.

3. **Import-light.** The CI runner installs no dependencies, so this file must
   import with stdlib + commands/cmdutils.py alone. `requests` is imported lazily
   inside LLMClient, never at module top.
"""

import logging
import re

from commands import cmdutils

log = logging.getLogger('MatterBot')

# Written into the props of every post the analyst makes. Reconstruction reads
# them back to work out what it is looking at:
#   reply    -- the analyst's narrative; replayed to the model as an assistant turn
#   evidence -- raw module output; deliberately NOT replayed (see reconstruct())
#   progress -- the "checking ..." interim note; never replayed
PROP_KEY = 'matterbot_ai'
PROP_REPLY = 'reply'
PROP_EVIDENCE = 'evidence'
PROP_PROGRESS = 'progress'
# Tools spent by a reply, so the per-thread cap survives a restart with no state.
PROP_TOOL_CALLS = 'ai_tool_calls'
# send_message() splits a long reply across several posts. These let reconstruct()
# put it back together as ONE assistant turn (and count its budget once).
PROP_MSG_ID = 'ai_message_id'
PROP_PART = 'ai_part'

# Characters to peel off a token before classifying it. Analysts write prose:
# indicators arrive in backticks, in parentheses, at the end of a sentence.
# Defanging (8.8.8[.]8) puts brackets INSIDE the token, never at the edges, so
# stripping edges is safe -- cmdutils.classify() refangs the rest.
_STRIP = ' \t\r\n`"\'*_,;:!?()<>[]{}.'

# Candidate splitting: whitespace is not enough. "8.8.8.8,evil.example.com" is one
# whitespace token but two indicators.
_CANDIDATE_SPLIT = re.compile(r'[\s,;|]+')
# [label](target) -- consider both halves; the label is often the defanged form.
_MARKDOWN_LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
# "IOC:evil.example.com", "ip=8.8.8.8", "sha256: abcd..."
_LABEL = re.compile(
    r'^(?:ioc|indicator|ip|ipv6|cidr|domain|host|url|hash|md5|sha1|sha256)\s*[:=]\s*',
    re.IGNORECASE,
)
_SCHEMES = ('http://', 'https://', 'hxxp://', 'hxxps://')
# What glues two indicators into one whitespace-free run: "8.8.8.8/1.1.1.1",
# "8.8.8.8->1.1.1.1", "evil[.]example[.]com/path". A bare '/' is also how a URL
# separates host from path, so this only ever gets applied to a token that has
# ALREADY failed to classify as a whole (see _candidates).
_JOIN_SPLIT = re.compile(r'/|->|→')

# Analysts defang (8[.]8[.]8[.]8, hxxps://) and label (IOC:, domain=) things they
# are actually flagging as indicators. Either signal means "trust me, this is
# real" and must bypass the domain-plausibility gate below -- a malicious domain
# in an oddball TLD is exactly the shape a real IOC takes, and dropping it because
# it does not match a known TLD table would be a silent, unexplained refusal.
_DEFANG_HINT = re.compile(r'\[\.\]|\(\.\)|\{\.\}|hxxp', re.IGNORECASE)

# The authoritative IANA delegated-TLD list -- every real TLD an analyst could
# possibly mean, and (just as important) nothing else. A hand-curated list of
# "common" gTLDs cannot win against ~1450 delegated ones: a reviewer showed real
# in-the-wild-abusable domains (c2.bond, evil.gdn, evil.surf, phish.mom, ...)
# were being silently dropped because they used a real TLD this file's authors
# had never heard of. Using the full list instead fixes both directions at
# once -- it accepts every real domain AND rejects prose/filenames like
# "report.doc" or "help.desk", because none of those endings are real TLDs.
#
#   Source:  https://data.iana.org/TLD/tlds-alpha-by-domain.txt
#   Version: 2026062302 (Last Updated Wed Jun 24 07:07:01 2026 UTC)
#   Regenerate: curl -s https://data.iana.org/TLD/tlds-alpha-by-domain.txt |
#               tail -n +2 | tr 'A-Z' 'a-z' | sort
#   (skip the first line -- it is a "# Version ..." comment, not a TLD)
_IANA_TLDS = frozenset({
    'aaa', 'aarp', 'abb', 'abbott', 'abbvie', 'abc', 'able', 'abogado', 'abudhabi',
    'ac', 'academy', 'accenture', 'accountant', 'accountants', 'aco', 'actor', 'ad',
    'ads', 'adult', 'ae', 'aeg', 'aero', 'aetna', 'af', 'afl', 'africa', 'ag',
    'agakhan', 'agency', 'ai', 'aig', 'airbus', 'airforce', 'airtel', 'akdn', 'al',
    'alibaba', 'alipay', 'allfinanz', 'allstate', 'ally', 'alsace', 'alstom', 'am',
    'amazon', 'americanexpress', 'americanfamily', 'amex', 'amfam', 'amica',
    'amsterdam', 'analytics', 'android', 'anquan', 'anz', 'ao', 'aol', 'apartments',
    'app', 'apple', 'aq', 'aquarelle', 'ar', 'arab', 'aramco', 'archi', 'army', 'arpa',
    'art', 'arte', 'as', 'asda', 'asia', 'associates', 'at', 'athleta', 'attorney',
    'au', 'auction', 'audi', 'audible', 'audio', 'auspost', 'author', 'auto', 'autos',
    'aw', 'aws', 'ax', 'axa', 'az', 'azure', 'ba', 'baby', 'baidu', 'banamex', 'band',
    'bank', 'bar', 'barcelona', 'barclaycard', 'barclays', 'barefoot', 'bargains',
    'baseball', 'basketball', 'bauhaus', 'bayern', 'bb', 'bbc', 'bbt', 'bbva', 'bcg',
    'bcn', 'bd', 'be', 'beats', 'beauty', 'beer', 'berlin', 'best', 'bestbuy', 'bet',
    'bf', 'bg', 'bh', 'bharti', 'bi', 'bible', 'bid', 'bike', 'bing', 'bingo', 'bio',
    'biz', 'bj', 'black', 'blackfriday', 'blockbuster', 'blog', 'bloomberg', 'blue',
    'bm', 'bms', 'bmw', 'bn', 'bnpparibas', 'bo', 'boats', 'boehringer', 'bofa', 'bom',
    'bond', 'boo', 'book', 'booking', 'bosch', 'bostik', 'boston', 'bot', 'boutique',
    'box', 'br', 'bradesco', 'bridgestone', 'broadway', 'broker', 'brother', 'brussels',
    'bs', 'bt', 'build', 'builders', 'business', 'buy', 'buzz', 'bv', 'bw', 'by', 'bz',
    'bzh', 'ca', 'cab', 'cafe', 'cal', 'call', 'calvinklein', 'cam', 'camera', 'camp',
    'canon', 'capetown', 'capital', 'capitalone', 'car', 'caravan', 'cards', 'care',
    'career', 'careers', 'cars', 'casa', 'case', 'cash', 'casino', 'cat', 'catering',
    'catholic', 'cba', 'cbn', 'cbre', 'cc', 'cd', 'center', 'ceo', 'cern', 'cf', 'cfa',
    'cfd', 'cg', 'ch', 'chanel', 'channel', 'charity', 'chase', 'chat', 'cheap',
    'chintai', 'christmas', 'chrome', 'church', 'ci', 'cipriani', 'circle', 'cisco',
    'citadel', 'citi', 'citic', 'city', 'ck', 'cl', 'claims', 'cleaning', 'click',
    'clinic', 'clinique', 'clothing', 'cloud', 'club', 'clubmed', 'cm', 'cn', 'co',
    'coach', 'codes', 'coffee', 'college', 'cologne', 'com', 'commbank', 'community',
    'company', 'compare', 'computer', 'comsec', 'condos', 'construction', 'consulting',
    'contact', 'contractors', 'cooking', 'cool', 'coop', 'corsica', 'country', 'coupon',
    'coupons', 'courses', 'cpa', 'cr', 'credit', 'creditcard', 'creditunion', 'cricket',
    'crown', 'crs', 'cruise', 'cruises', 'cu', 'cuisinella', 'cv', 'cw', 'cx', 'cy',
    'cymru', 'cyou', 'cz', 'dad', 'dance', 'data', 'date', 'dating', 'datsun', 'day',
    'dclk', 'dds', 'de', 'deal', 'dealer', 'deals', 'degree', 'delivery', 'dell',
    'deloitte', 'delta', 'democrat', 'dental', 'dentist', 'desi', 'design', 'dev',
    'dhl', 'diamonds', 'diet', 'digital', 'direct', 'directory', 'discount', 'discover',
    'dish', 'diy', 'dj', 'dk', 'dm', 'dnp', 'do', 'docs', 'doctor', 'dog', 'domains',
    'dot', 'download', 'drive', 'dtv', 'dubai', 'dupont', 'durban', 'dvag', 'dvr', 'dz',
    'earth', 'eat', 'ec', 'eco', 'edeka', 'edu', 'education', 'ee', 'eg', 'email',
    'emerck', 'energy', 'engineer', 'engineering', 'enterprises', 'epson', 'equipment',
    'er', 'ericsson', 'erni', 'es', 'esq', 'estate', 'et', 'eu', 'eurovision', 'eus',
    'events', 'exchange', 'expert', 'exposed', 'express', 'extraspace', 'fage', 'fail',
    'fairwinds', 'faith', 'family', 'fan', 'fans', 'farm', 'farmers', 'fashion', 'fast',
    'fedex', 'feedback', 'ferrari', 'ferrero', 'fi', 'fidelity', 'fido', 'film',
    'final', 'finance', 'financial', 'fire', 'firestone', 'firmdale', 'fish', 'fishing',
    'fit', 'fitness', 'fj', 'fk', 'flickr', 'flights', 'flir', 'florist', 'flowers',
    'fly', 'fm', 'fo', 'foo', 'food', 'football', 'ford', 'forex', 'forsale', 'forum',
    'foundation', 'fox', 'fr', 'free', 'fresenius', 'frl', 'frogans', 'frontier', 'ftr',
    'fujitsu', 'fun', 'fund', 'furniture', 'futbol', 'fyi', 'ga', 'gal', 'gallery',
    'gallo', 'gallup', 'game', 'games', 'gap', 'garden', 'gay', 'gb', 'gbiz', 'gd',
    'gdn', 'ge', 'gea', 'gent', 'genting', 'george', 'gf', 'gg', 'ggee', 'gh', 'gi',
    'gift', 'gifts', 'gives', 'giving', 'gl', 'glass', 'gle', 'global', 'globo', 'gm',
    'gmail', 'gmbh', 'gmo', 'gmx', 'gn', 'godaddy', 'gold', 'goldpoint', 'golf',
    'goodyear', 'goog', 'google', 'gop', 'got', 'gov', 'gp', 'gq', 'gr', 'grainger',
    'graphics', 'gratis', 'green', 'gripe', 'grocery', 'group', 'gs', 'gt', 'gu',
    'gucci', 'guge', 'guide', 'guitars', 'guru', 'gw', 'gy', 'hair', 'hamburg',
    'hangout', 'haus', 'hbo', 'hdfc', 'hdfcbank', 'health', 'healthcare', 'help',
    'helsinki', 'here', 'hermes', 'hiphop', 'hisamitsu', 'hitachi', 'hiv', 'hk', 'hkt',
    'hm', 'hn', 'hockey', 'holdings', 'holiday', 'homedepot', 'homegoods', 'homes',
    'homesense', 'honda', 'horse', 'hospital', 'host', 'hosting', 'hot', 'hotels',
    'hotmail', 'house', 'how', 'hr', 'hsbc', 'ht', 'hu', 'hughes', 'hyatt', 'hyundai',
    'ibm', 'icbc', 'ice', 'icu', 'id', 'ie', 'ieee', 'ifm', 'ikano', 'il', 'im',
    'imamat', 'imdb', 'immo', 'immobilien', 'in', 'inc', 'industries', 'infiniti',
    'info', 'ing', 'ink', 'institute', 'insurance', 'insure', 'int', 'international',
    'intuit', 'investments', 'io', 'ipiranga', 'iq', 'ir', 'irish', 'is', 'ismaili',
    'ist', 'istanbul', 'it', 'itau', 'itv', 'jaguar', 'java', 'jcb', 'je', 'jeep',
    'jetzt', 'jewelry', 'jio', 'jll', 'jm', 'jmp', 'jnj', 'jo', 'jobs', 'joburg', 'jot',
    'joy', 'jp', 'jpmorgan', 'jprs', 'juegos', 'juniper', 'kaufen', 'kddi', 'ke',
    'kerryhotels', 'kerryproperties', 'kfh', 'kg', 'kh', 'ki', 'kia', 'kids', 'kim',
    'kindle', 'kitchen', 'kiwi', 'km', 'kn', 'koeln', 'komatsu', 'kosher', 'kp', 'kpmg',
    'kpn', 'kr', 'krd', 'kred', 'kuokgroup', 'kw', 'ky', 'kyoto', 'kz', 'la', 'lacaixa',
    'lamborghini', 'lamer', 'land', 'landrover', 'lanxess', 'lasalle', 'lat', 'latino',
    'latrobe', 'law', 'lawyer', 'lb', 'lc', 'lds', 'lease', 'leclerc', 'lefrak',
    'legal', 'lego', 'lexus', 'lgbt', 'li', 'lidl', 'life', 'lifeinsurance',
    'lifestyle', 'lighting', 'like', 'lilly', 'limited', 'limo', 'lincoln', 'link',
    'live', 'living', 'lk', 'llc', 'llp', 'loan', 'loans', 'locker', 'locus', 'lol',
    'london', 'lotte', 'lotto', 'love', 'lpl', 'lplfinancial', 'lr', 'ls', 'lt', 'ltd',
    'ltda', 'lu', 'lundbeck', 'luxe', 'luxury', 'lv', 'ly', 'ma', 'madrid', 'maif',
    'maison', 'makeup', 'man', 'management', 'mango', 'map', 'market', 'marketing',
    'markets', 'marriott', 'marshalls', 'mattel', 'mba', 'mc', 'mckinsey', 'md', 'me',
    'med', 'media', 'meet', 'melbourne', 'meme', 'memorial', 'men', 'menu', 'merck',
    'merckmsd', 'mg', 'mh', 'miami', 'microsoft', 'mil', 'mini', 'mint', 'mit',
    'mitsubishi', 'mk', 'ml', 'mlb', 'mls', 'mm', 'mma', 'mn', 'mo', 'mobi', 'mobile',
    'moda', 'moe', 'moi', 'mom', 'monash', 'money', 'monster', 'mormon', 'mortgage',
    'moscow', 'moto', 'motorcycles', 'mov', 'movie', 'mp', 'mq', 'mr', 'ms', 'msd',
    'mt', 'mtn', 'mtr', 'mu', 'museum', 'music', 'mv', 'mw', 'mx', 'my', 'mz', 'na',
    'nab', 'nagoya', 'name', 'navy', 'nba', 'nc', 'ne', 'nec', 'net', 'netbank',
    'netflix', 'network', 'neustar', 'new', 'news', 'next', 'nextdirect', 'nexus', 'nf',
    'nfl', 'ng', 'ngo', 'nhk', 'ni', 'nico', 'nike', 'nikon', 'ninja', 'nissan',
    'nissay', 'nl', 'no', 'nokia', 'norton', 'now', 'nowruz', 'nowtv', 'np', 'nr',
    'nra', 'nrw', 'ntt', 'nu', 'nyc', 'nz', 'obi', 'observer', 'office', 'okinawa',
    'olayan', 'olayangroup', 'ollo', 'om', 'omega', 'one', 'ong', 'onl', 'online',
    'ooo', 'open', 'oracle', 'orange', 'org', 'organic', 'origins', 'osaka', 'otsuka',
    'ott', 'ovh', 'pa', 'page', 'panasonic', 'paris', 'pars', 'partners', 'parts',
    'party', 'pay', 'pccw', 'pe', 'pet', 'pf', 'pfizer', 'pg', 'ph', 'pharmacy', 'phd',
    'philips', 'phone', 'photo', 'photography', 'photos', 'physio', 'pics', 'pictet',
    'pictures', 'pid', 'pin', 'ping', 'pink', 'pioneer', 'pizza', 'pk', 'pl', 'place',
    'play', 'playstation', 'plumbing', 'plus', 'pm', 'pn', 'pnc', 'pohl', 'poker',
    'politie', 'porn', 'post', 'pr', 'praxi', 'press', 'prime', 'pro', 'prod',
    'productions', 'prof', 'progressive', 'promo', 'properties', 'property',
    'protection', 'pru', 'prudential', 'ps', 'pt', 'pub', 'pw', 'pwc', 'py', 'qa',
    'qpon', 'quebec', 'quest', 'racing', 'radio', 're', 'read', 'realestate', 'realtor',
    'realty', 'recipes', 'red', 'redumbrella', 'rehab', 'reise', 'reisen', 'reit',
    'reliance', 'ren', 'rent', 'rentals', 'repair', 'report', 'republican', 'rest',
    'restaurant', 'review', 'reviews', 'rexroth', 'rich', 'richardli', 'ricoh', 'ril',
    'rio', 'rip', 'ro', 'rocks', 'rodeo', 'rogers', 'room', 'rs', 'rsvp', 'ru', 'rugby',
    'ruhr', 'run', 'rw', 'rwe', 'ryukyu', 'sa', 'saarland', 'safe', 'safety', 'sakura',
    'sale', 'salon', 'samsclub', 'samsung', 'sandvik', 'sandvikcoromant', 'sanofi',
    'sap', 'sarl', 'sas', 'save', 'saxo', 'sb', 'sbi', 'sbs', 'sc', 'scb', 'schaeffler',
    'schmidt', 'scholarships', 'school', 'schule', 'schwarz', 'science', 'scot', 'sd',
    'se', 'search', 'seat', 'secure', 'security', 'seek', 'select', 'sener', 'services',
    'seven', 'sew', 'sex', 'sexy', 'sfr', 'sg', 'sh', 'shangrila', 'sharp', 'shell',
    'shia', 'shiksha', 'shoes', 'shop', 'shopping', 'shouji', 'show', 'si', 'silk',
    'sina', 'singles', 'site', 'sj', 'sk', 'ski', 'skin', 'sky', 'skype', 'sl', 'sling',
    'sm', 'smart', 'smile', 'sn', 'sncf', 'so', 'soccer', 'social', 'softbank',
    'software', 'sohu', 'solar', 'solutions', 'song', 'sony', 'soy', 'spa', 'space',
    'sport', 'spot', 'sr', 'srl', 'ss', 'st', 'stada', 'staples', 'star', 'statebank',
    'statefarm', 'stc', 'stcgroup', 'stockholm', 'storage', 'store', 'stream', 'studio',
    'study', 'style', 'su', 'sucks', 'supplies', 'supply', 'support', 'surf', 'surgery',
    'suzuki', 'sv', 'swatch', 'swiss', 'sx', 'sy', 'sydney', 'systems', 'sz', 'tab',
    'taipei', 'talk', 'taobao', 'target', 'tatamotors', 'tatar', 'tattoo', 'tax',
    'taxi', 'tc', 'tci', 'td', 'tdk', 'team', 'tech', 'technology', 'tel', 'temasek',
    'tennis', 'teva', 'tf', 'tg', 'th', 'thd', 'theater', 'theatre', 'tiaa', 'tickets',
    'tienda', 'tips', 'tires', 'tirol', 'tj', 'tjmaxx', 'tjx', 'tk', 'tkmaxx', 'tl',
    'tm', 'tmall', 'tn', 'to', 'today', 'tokyo', 'tools', 'top', 'toray', 'toshiba',
    'total', 'tours', 'town', 'toyota', 'toys', 'tr', 'trade', 'trading', 'training',
    'travel', 'travelers', 'travelersinsurance', 'trust', 'trv', 'tt', 'tube', 'tui',
    'tunes', 'tushu', 'tv', 'tvs', 'tw', 'tz', 'ua', 'ubank', 'ubs', 'ug', 'uk',
    'unicom', 'university', 'uno', 'uol', 'ups', 'us', 'uy', 'uz', 'va', 'vacations',
    'vana', 'vanguard', 'vc', 've', 'vegas', 'ventures', 'verisign', 'versicherung',
    'vet', 'vg', 'vi', 'viajes', 'video', 'vig', 'viking', 'villas', 'vin', 'vip',
    'virgin', 'visa', 'vision', 'viva', 'vivo', 'vlaanderen', 'vn', 'vodka', 'volvo',
    'vote', 'voting', 'voto', 'voyage', 'vu', 'wales', 'walmart', 'walter', 'wang',
    'wanggou', 'watch', 'watches', 'weather', 'weatherchannel', 'webcam', 'weber',
    'website', 'wed', 'wedding', 'weibo', 'weir', 'wf', 'whoswho', 'wien', 'wiki',
    'williamhill', 'win', 'windows', 'wine', 'winners', 'wme', 'woodside', 'work',
    'works', 'world', 'wow', 'ws', 'wtc', 'wtf', 'xbox', 'xerox', 'xihuan', 'xin',
    'xn--11b4c3d', 'xn--1ck2e1b', 'xn--1qqw23a', 'xn--2scrj9c', 'xn--30rr7y',
    'xn--3bst00m', 'xn--3ds443g', 'xn--3e0b707e', 'xn--3hcrj9c', 'xn--3pxu8k',
    'xn--42c2d9a', 'xn--45br5cyl', 'xn--45brj9c', 'xn--45q11c', 'xn--4dbrk0ce',
    'xn--4gbrim', 'xn--54b7fta0cc', 'xn--55qw42g', 'xn--55qx5d', 'xn--5su34j936bgsg',
    'xn--5tzm5g', 'xn--6frz82g', 'xn--6qq986b3xl', 'xn--80adxhks', 'xn--80ao21a',
    'xn--80aqecdr1a', 'xn--80asehdb', 'xn--80aswg', 'xn--8y0a063a', 'xn--90a3ac',
    'xn--90ae', 'xn--90ais', 'xn--9dbq2a', 'xn--9et52u', 'xn--9krt00a',
    'xn--b4w605ferd', 'xn--bck1b9a5dre4c', 'xn--c1avg', 'xn--c2br7g', 'xn--cck2b3b',
    'xn--cckwcxetd', 'xn--cg4bki', 'xn--clchc0ea0b2g2a9gcd', 'xn--czr694b',
    'xn--czrs0t', 'xn--czru2d', 'xn--d1acj3b', 'xn--d1alf', 'xn--e1a4c',
    'xn--eckvdtc9d', 'xn--efvy88h', 'xn--fct429k', 'xn--fhbei', 'xn--fiq228c5hs',
    'xn--fiq64b', 'xn--fiqs8s', 'xn--fiqz9s', 'xn--fjq720a', 'xn--flw351e',
    'xn--fpcrj9c3d', 'xn--fzc2c9e2c', 'xn--fzys8d69uvgm', 'xn--g2xx48c', 'xn--gckr3f0f',
    'xn--gecrj9c', 'xn--gk3at1e', 'xn--h2breg3eve', 'xn--h2brj9c', 'xn--h2brj9c8c',
    'xn--hxt814e', 'xn--i1b6b1a6a2e', 'xn--imr513n', 'xn--io0a7i', 'xn--j1aef',
    'xn--j1amh', 'xn--j6w193g', 'xn--jlq480n2rg', 'xn--jvr189m', 'xn--kcrx77d1x4a',
    'xn--kprw13d', 'xn--kpry57d', 'xn--kput3i', 'xn--l1acc', 'xn--lgbbat1ad8j',
    'xn--mgb9awbf', 'xn--mgba3a3ejt', 'xn--mgba3a4f16a', 'xn--mgba7c0bbn0a',
    'xn--mgbaam7a8h', 'xn--mgbab2bd', 'xn--mgbah1a3hjkrd', 'xn--mgbai9azgqp6j',
    'xn--mgbayh7gpa', 'xn--mgbbh1a', 'xn--mgbbh1a71e', 'xn--mgbc0a9azcg',
    'xn--mgbca7dzdo', 'xn--mgbcpq6gpa1a', 'xn--mgberp4a5d4ar', 'xn--mgbgu82a',
    'xn--mgbi4ecexp', 'xn--mgbpl2fh', 'xn--mgbt3dhd', 'xn--mgbtx2b', 'xn--mgbx4cd0ab',
    'xn--mix891f', 'xn--mk1bu44c', 'xn--mxtq1m', 'xn--ngbc5azd', 'xn--ngbe9e0a',
    'xn--ngbrx', 'xn--node', 'xn--nqv7f', 'xn--nqv7fs00ema', 'xn--nyqy26a',
    'xn--o3cw4h', 'xn--ogbpf8fl', 'xn--otu796d', 'xn--p1acf', 'xn--p1ai', 'xn--pgbs0dh',
    'xn--pssy2u', 'xn--q7ce6a', 'xn--q9jyb4c', 'xn--qcka1pmc', 'xn--qxa6a', 'xn--qxam',
    'xn--rhqv96g', 'xn--rovu88b', 'xn--rvc1e0am3e', 'xn--s9brj9c', 'xn--ses554g',
    'xn--t60b56a', 'xn--tckwe', 'xn--tiq49xqyj', 'xn--unup4y',
    'xn--vermgensberater-ctb', 'xn--vermgensberatung-pwb', 'xn--vhquv', 'xn--vuq861b',
    'xn--w4r85el8fhu5dnra', 'xn--w4rs40l', 'xn--wgbh1c', 'xn--wgbl6a', 'xn--xhq521b',
    'xn--xkc2al3hye2a', 'xn--xkc2dl3a5ee0h', 'xn--y9a3aq', 'xn--yfro4i67o',
    'xn--ygbi2ammx', 'xn--zfr164b', 'xxx', 'xyz', 'yachts', 'yahoo', 'yamaxun',
    'yandex', 'ye', 'yodobashi', 'yoga', 'yokohama', 'you', 'youtube', 'yt', 'yun',
    'za', 'zappos', 'zara', 'zero', 'zip', 'zm', 'zone', 'zuerich', 'zw',
})
# File extensions that would otherwise be misread as a domain because they
# happen to ALSO be real IANA TLDs -- ".zip" and ".py" are both live delegated
# TLDs, so the plain IANA-membership check above cannot tell "payload.zip is the
# sample" from a genuine evil.zip domain on its own. This list is deliberately
# small: it is exactly the intersection of {common file extensions} and
# {real IANA TLDs}, checked BEFORE the membership check so the collision always
# resolves to "not a domain". Domain-dominant collisions (.com, .cc, .io, .ai,
# .co -- all real TLDs that are also short strings, but whose domain use vastly
# outweighs any file-extension reading) are deliberately NOT here.
# NOTE: genuine .zip/.py/... domains are rare but rescuable via defanging
# (evil[.]zip) or labelling (domain=evil.zip), which signals analyst intent.
_FILE_EXT_BLOCKLIST = frozenset({
    'py', 'sh', 'md', 'so', 'pl', 'rs', 'ps', 'zip', 'mov',
})


def _is_plausible_tld(tld):
    """Is `tld` a TLD an analyst would plausibly mean, vs. a file extension?

    cmdutils._HOSTNAME_RE only requires the final label to be alphabetic, so
    "malware.exe" and "it.then" (a run-together sentence) classify as domains
    just as readily as "evil.com" does. This is the gate that tells them apart:
    membership in the authoritative IANA TLD list (_IANA_TLDS) decides it, which
    settles both directions at once -- every real TLD is in that list, and
    prose/filenames ("report.doc", "help.desk", "oauth.token") are not. The one
    exception is _FILE_EXT_BLOCKLIST, checked first: a handful of file
    extensions collide with a genuinely real TLD (.zip, .py, ...), and for those
    the file-extension reading is overwhelmingly more common in SOC chat.
    Bias toward accepting when unsure -- see _signals_intent().
    """
    tld = tld.lower()
    if tld in _FILE_EXT_BLOCKLIST:
        return False
    return tld in _IANA_TLDS


def _signals_intent(original_token, candidate):
    """Did the analyst mark `candidate` as an indicator, defanged or labelled?

    A defanged token (brackets, hxxp) or a labelled one (IOC:, domain=) is the
    analyst stating "this is an indicator" in their own words. That statement
    outranks the TLD-plausibility gate: a real malicious domain in an unusual
    TLD must never be silently dropped because it is not in our TLD tables.
    """
    if _DEFANG_HINT.search(candidate):
        return True
    return bool(_LABEL.match(original_token.strip(_STRIP)))


def _candidates(token):
    """Every string worth handing to cmdutils.classify() for one prose token.

    If the token ALREADY classifies as an indicator whole, that is authoritative
    and it is returned alone: a CIDR's network address ("10.0.0.0/8") must not
    also be offered as a second, independent IP, and a defanged URL with a path
    must not also be offered as its bare host. Only a token that does NOT
    classify whole gets split further -- a scheme-less run of two indicators
    glued by '/', '->' or an arrow ("8.8.8.8/1.1.1.1", "8.8.8.8->1.1.1.1", a bare
    host with a URL path) is not itself one indicator, so every resulting
    segment is offered as a candidate and cmdutils.classify() decides, per
    segment, which (if any) are real. A scheme-bearing token that still fails to
    classify is left alone -- a URL's own path is full of '/' and must not be
    torn apart.
    """
    token = token.strip(_STRIP)
    if not token:
        return []
    token = _LABEL.sub('', token).strip(_STRIP)
    if not token:
        return []
    _, indicator_type = cmdutils.classify(token)
    if indicator_type:
        return [token]
    if token.lower().startswith(_SCHEMES):
        return [token]
    segments = [seg.strip(_STRIP) for seg in _JOIN_SPLIT.split(token)]
    segments = [seg for seg in segments if seg]
    return segments or [token]


def extract_indicators(text):
    """Map every indicator in free text to its canonical cmdutils type.

    cmdutils.classify() types one clean token; an analyst hands us a sentence.
    This is the bridge, and it is load-bearing twice over: it builds the
    `authorized` set (what the model is allowed to look up at all) and it decides
    which modules are exposed this turn.

    A domain result additionally passes a plausibility gate (_is_plausible_tld):
    cmdutils._HOSTNAME_RE only requires an alphabetic final label, so ordinary
    prose ("checked it.Then rebooted") and filenames ("malware.exe") classify as
    domains just as readily as real ones do, and SOC chat is full of both. The
    gate is skipped -- accept unconditionally -- when the analyst defanged or
    labelled the token (_signals_intent): that is the analyst stating this is an
    indicator, and a missed real IOC is worse than an admitted filename.
    """
    found = {}
    if not text:
        return found
    # Flatten markdown links so BOTH the label and the target get classified.
    working = _MARKDOWN_LINK.sub(lambda m: f'{m.group(1)} {m.group(2)}', text)
    for token in _CANDIDATE_SPLIT.split(working):
        for candidate in _candidates(token):
            value, indicator_type = cmdutils.classify(candidate)
            if not indicator_type:
                continue
            if indicator_type == cmdutils.DOMAIN and not _signals_intent(token, candidate):
                if not _is_plausible_tld(value.rsplit('.', 1)[-1]):
                    # This is the ONLY place an indicator-shaped token gets
                    # silently dropped. Log it -- an operator debugging "why
                    # didn't the AI look that up?" needs something to grep for.
                    log.debug('extract_indicators: rejected %r (implausible TLD)', value)
                    continue
            found[value] = indicator_type
    return found


REDACTED = '<redacted>'

# Credentials in a URL query string -- the exact shape #285/#286 found in
# botscout/proxycheck/mwdb, and the shape a module's SUCCESS output can carry too
# (a "source" link, a cited API URL).
_QUERY_CRED_RE = re.compile(
    r'(?i)([?&](?:api[-_]?key|apikey|key|token|access[-_]?token|auth|secret|password|passwd|pwd)=)'
    r'([^\s&"\'<>]+)'
)
# Labelled secrets anywhere in the text. Deliberately does NOT include a bare
# "key", which appears constantly in legitimate module output ("Key | Value").
_LABELLED_CRED_RE = re.compile(
    r'(?i)\b(api[-_]?key|apikey|access[-_]?token|token|secret|password|passwd)\b(\s*[:=]\s*)'
    r'([^\s"\'<>]{6,})'
)
_BEARER_RE = re.compile(r'(?i)\b(bearer)\s+([A-Za-z0-9._\-]{8,})')


def sanitize_tool_output(text):
    """Strip credentials out of module output before it leaves this process.

    Do NOT rely on the modules for this, and do NOT rely on #286: that fixed the
    exception text of three modules, while a module's *success* output can carry
    a key-bearing source URL just as easily. And unlike an @-command -- whose
    output only ever reaches a Mattermost channel -- the AI ships this text to a
    third-party LLM endpoint. Redact once, here, on the way out.
    """
    if not text:
        return text
    out = _QUERY_CRED_RE.sub(lambda m: f'{m.group(1)}{REDACTED}', text)
    out = _LABELLED_CRED_RE.sub(lambda m: f'{m.group(1)}{m.group(2)}{REDACTED}', out)
    out = _BEARER_RE.sub(lambda m: f'{m.group(1)} {REDACTED}', out)
    return out


def build_tool_definitions(registry, relevant_types):
    """Generate OpenAI-format tool schemas from metadata the modules already carry.

    No new metadata to author: the name is the module name, the description is its
    existing HELP['DEFAULT']['desc'] plus its ACCEPTS types, and the single `query`
    parameter is the indicator.

    Exposure is narrowed to modules that accept an indicator type actually in play.
    No indicators anywhere in the case -> no tools at all, and the model simply
    converses from context. `registry` is expected to be pre-filtered by the
    operator allow-list (see AIAnalyst._registry).
    """
    tools = []
    if not relevant_types:
        return tools
    for name in sorted(registry):
        entry = registry[name] or {}
        if not entry.get('aitool'):
            continue
        accepts = entry.get('accepts')
        if accepts and not set(accepts) & set(relevant_types):
            continue
        help_text = (entry.get('help') or {}).get('DEFAULT') or {}
        desc = help_text.get('desc') or 'No help available.'
        types = ', '.join(accepts) if accepts else cmdutils.TYPES_HUMAN
        tools.append({
            'type': 'function',
            'function': {
                'name': name,
                'description': f'{desc} Accepts: {types}',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': f'the indicator to look up ({types})',
                        },
                    },
                    'required': ['query'],
                },
            },
        })
    return tools


def normalise_thread(payload, exclude_post_id=None):
    """Turn a raw mmDriver.posts.get_thread() payload into ordered posts.

    Lives here rather than in matterbot.py so it is testable: matterbot.py cannot
    be imported under the dependency-free CI runner. The caller passes the driver's
    dict through untouched.

    The current post is excluded: the webhook fires once the post exists, so the
    thread we fetch usually already contains the message we are answering, and it
    must be applied separately (see AIAnalyst.handle) for the pending-pivot handoff
    to land on this turn.
    """
    posts = ((payload or {}).get('posts') or {}).values()
    ordered = sorted(posts, key=lambda p: (p.get('create_at') or 0, p.get('id') or ''))
    return [p for p in ordered if p.get('id') != exclude_post_id]


# A pivot is approved the way analysts actually approve one: by saying yes, not by
# re-typing the indicator. The reading is deliberately shallow -- and deliberately
# refuses to read a HEDGED yes as a yes. "ok but why would that domain matter?"
# starts with an affirmative and approves nothing; any negation or contrast word
# disqualifies the whole message. A missed yes costs one extra round-trip; a
# false yes runs a lookup the analyst did not ask for.
_AFFIRMATIVE_WORDS = {
    'yes', 'y', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'affirmative',
    'proceed', 'please',
}
_AFFIRMATIVE_PHRASES = (
    'go ahead', 'do it', 'please do', 'go for it', 'pull it', 'check it', 'yes please',
)
_NEGATIONS = {
    'no', 'nope', 'nah', 'not', "don't", 'dont', 'never', 'but', 'except',
    'without', 'skip', 'hold', 'wait', 'stop',
}

_MODES = ('full', 'brief')


def _strip_bind(text, bind):
    """Lowercase the message and drop a leading bind mention, if present."""
    words = (text or '').strip().split()
    if words and words[0].lower() == bind.lower():
        words = words[1:]
    return ' '.join(words).strip().lower()


def is_affirmative(text, bind):
    """Whether a user turn approves the pivot the analyst just proposed."""
    words = _strip_bind(text, bind).split()
    # A mode toggle is not an answer; look past it ("@ai full yes").
    if words and words[0] in _MODES:
        words = words[1:]
    if not words:
        return False
    cleaned = [w.strip(_STRIP) for w in words]
    # Any negation or contrast anywhere disqualifies. A hedged yes is not a yes.
    if any(word in _NEGATIONS for word in cleaned):
        return False
    norm = ' '.join(cleaned)
    if any(norm.startswith(phrase) for phrase in _AFFIRMATIVE_PHRASES):
        return True
    return cleaned[0] in _AFFIRMATIVE_WORDS


def evidence_mode(text, bind):
    """The `@ai full` / `@ai brief` toggle, or None if this turn does not set one.

    Only the word immediately after the bind counts, so "give me the full picture"
    is prose, not a mode switch.
    """
    words = _strip_bind(text, bind).split()
    if words and words[0] in _MODES:
        return words[0]
    return None


class ThreadState(object):
    """Everything the analyst knows about a case, derived from the thread alone.

    Nothing here is persisted: reconstruct() rebuilds it from the Mattermost posts
    on every turn. That is what makes a restart or a redeploy cost zero session
    loss, and what keeps two cases in one channel from bleeding into each other.
    """

    def __init__(self, mode='compact'):
        self.history = []           # [{'role': 'user'|'assistant', 'content': str}]
        self.authorized = {}        # indicator -> type; the model MAY look these up
        self.pending = {}           # indicator -> type; proposed, awaiting a yes
        self.mode = mode            # 'compact' | 'full'
        self.tool_calls_used = 0    # tools already spent in this thread


def apply_user_message(state, text, bind):
    """Fold one user turn into the state.

    Order matters. A pending pivot is consumed by *this* message before the
    message's own indicators are added, because that is the sequence the analyst
    experienced: the bot proposed, and now they are answering it.
    """
    if state.pending and is_affirmative(text, bind):
        state.authorized.update(state.pending)
    # Either way the proposal is now answered; it does not stay open across turns.
    # An analyst who instead NAMES an indicator authorizes exactly that one, below.
    state.pending = {}
    mode = evidence_mode(text, bind)
    if mode:
        state.mode = 'full' if mode == 'full' else 'compact'
    # Anything the analyst names, the analyst has authorized. This is the only way
    # an indicator legitimately enters the authorized set unprompted.
    state.authorized.update(extract_indicators(text))


def reconstruct(posts, bot_id, default_mode, max_history_turns, bind):
    """Rebuild ThreadState from a thread's posts, chronologically ordered.

    `posts` are dicts with 'user_id', 'message' and 'props' (see normalise_thread).
    The current, unanswered post must NOT be in this list -- the caller applies it
    via apply_user_message(), so the pending-pivot handoff lands on it.
    """
    state = ThreadState(mode=default_mode)
    open_reply_id = None    # the ai_message_id of the reply we are still assembling
    for post in posts:
        message = post.get('message') or ''
        props = post.get('props') or {}
        if post.get('user_id') == bot_id:
            if props.get(PROP_KEY) != PROP_REPLY:
                # Evidence dumps, progress notes, and output from ordinary
                # @-commands sharing this thread. None of it is the analyst's
                # narrative, so none of it is the model's memory.
                continue
            msg_id = props.get(PROP_MSG_ID)
            is_continuation = (
                msg_id is not None
                and msg_id == open_reply_id
                and state.history
                and state.history[-1]['role'] == 'assistant'
            )
            if is_continuation:
                # A split reply: same logical message, more text. Do NOT re-charge
                # the tool budget -- every part carries the same ai_tool_calls.
                state.history[-1]['content'] += '\n' + message
            else:
                try:
                    state.tool_calls_used += int(props.get(PROP_TOOL_CALLS) or 0)
                except (TypeError, ValueError):
                    pass
                state.history.append({'role': 'assistant', 'content': message})
                open_reply_id = msg_id
            # Recompute against the WHOLE reply, since the pivot may be named in a
            # later part. Whatever the bot named that is not yet authorized is a
            # proposal awaiting a yes.
            state.pending = {
                value: itype
                for value, itype in extract_indicators(state.history[-1]['content']).items()
                if value not in state.authorized
            }
        else:
            open_reply_id = None
            apply_user_message(state, message, bind)
            state.history.append({'role': 'user', 'content': message})
    # Bound the model's context, NOT its authorization: the cap trims history only.
    # authorized/pending/mode/budget were folded from every post above, so an
    # indicator named 30 turns ago stays approved after it scrolls out of context.
    if max_history_turns and len(state.history) > max_history_turns:
        state.history = state.history[-max_history_turns:]
    return state
