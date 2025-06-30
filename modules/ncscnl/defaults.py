#!/usr/bin/env python3

NAME = "NCSC-NL Advisories"
URL = "https://advisories.ncsc.nl/rss/advisories"
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Government",
    "Vulnerabilities"
)
ENTRIES = 30
ADMIN_ONLY = False

# The AUTOADVISORY feature is really only useful if you are using other
# related bot modules, such as Qualys, and the bot can 'call itself'.
# E.g.: you would need something like '@qualys sw' as the command.
# The bot will append the product name to the command, to tell itself to
# check if any assets are using the product/software/vendor in question.
# True = enabled, False = disabled
AUTOADVISORY = False
# Format: 'channel name': [ 'command1', 'command2', ... ]
ADVISORYCHANS = {
}
# History file used to prevent double-posting.
HISTORY = "history.cache"
# Filter to base the history on (part that gets stored in the history file)
HISTORYFILTER = (
    r'NCSC-\d{1,4}-\d{1,4} \[\d{1}\.\d{1,2}] \[[hHmMlL]/[hHmMlL]\]',
)
# Title filter: remove all parts of the title with this part in it. Useful
# for removing generic terms such as 'products', in order to improve asset
# management query accuracy. Can be a regular expression as well!
TITLEFILTER = (
)
# List of e.g. chance/impact levels to check up (or not). This is probably
# fine in its default configuration, if you are only looking at severities.
# You could also use other strings to wildcard match on here; they are
# tested against the RSS entry's title.
LOOKUPVALUES = (
    r'\[[hH]/[hH]\]',
    r'\[[hH]/[mM]\]',
    r'\[[mM]/[hH]\]',
    r'\[[hH]/[lL]\]',
    r'\[[lL]/[hH]\]',
)
# Usually, the titles will be in a somewhat syntactically consistent format.
# For NCSC NL feeds, the relevant product names always seem to appear in the
# RSS entry's title, after 'Kwetsbaarheid' or 'Kwetsbaarheden' 'verholpen in'.
PRODUCTSPLIT = [
    'Kwetsbaarheid verholpen in ',
    'Kwetsbaarheden verholpen in ',
]
