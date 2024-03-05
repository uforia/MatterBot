#!/usr/bin/env python3

BINDS = ['@docgen']
CHANS = ['debug']
CONTENTTYPE = 'application/json'
APIURL = {
    'docgen':   {
        'url': '<your WikiJS instance\'s URL here>',
        'key': '<your WikiJS\' API token here>',
    },
}
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'This module is used for document processing: generating documents, creating resources such as image uploads, parsing response plan surveys, etc.',
    },
    '<language>': {
        'args': '<casenumber>',
        'desc': 'Generate a new composite PDF document in the language `language` for case number `casenumber`. ISO language codes should be configured/used wherever possible, including on the Wiki for page block separation. For example: `@docgen en_US memo 2023041101`.',
    },
    'upload': {
        'args': '<comments> (optional!)',
        'desc': 'The module will take the attached image(s) and create a separate Wiki page for every one (with the optional comment(s)). They can then be easily included into other documents.',
    },
    'parse': {
        'args': '<title>',
        'desc': 'The module will take the attached Excel/CSV file and attempt to parse its contents, creating a questions & answers page on the Wiki with the given title.',
    },
}
TEMPLATECASES = 'Template Cases'
TEMPLATEIDCHAIN = 'Template ID Chain'
TEMPLATECUSTOMERS = 'Template Customers'
# Set your default language
DEFAULTLOCALE = "en_US"
# Set your template directory
TEMPLATEDIR = "my_fancy_business_template/"
# Map the template entries to files
LANGMAP = {
    'en_US': {
        'toc': TEMPLATEDIR+"toc_en.html",
        'css': TEMPLATEDIR+"your_css.css",
        'header': TEMPLATEDIR+"header_en.html",
        'footer': TEMPLATEDIR+"footer_en.html",
        'titlebreak': TEMPLATEDIR+"titlebreak_en.html",
        'pagebreak': TEMPLATEDIR+"titlebreak_en.html",
    },
}