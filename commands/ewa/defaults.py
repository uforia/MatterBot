#!/usr/bin/env python3

BINDS = ['@ewa']
CHANS = ['debug']
CONTENTTYPE = 'application/json'
APIURL = {
    'ewa': {
        'url': '<your WikiJS instance\'s URL here>',
        'token': '<your WikiJS\' API token here>',
    },
    'nvd': {
        'url': 'https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=',
    },
}
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'This module can be used to create early warnings/advisories and publish them as PDFs',
    },
    'create': {
        'args': '<CVE ID>',
        'desc': 'Create a WikiJS entry for the specified CVE-ID. Example: `... create CVE-2021-44228`'
    },
    'pdf': {
        'args': '<CVE ID>',
        'desc': 'Generate a PDF from the WikiJS page for the CVE-ID. Example: `... pdf CVE-2021-44228`'
    },
}
LOCALE = "en_US"
EWAHEADER = "<your advisory name>"
TAGS = "\"1\", \"2\", \"3\""
VULNTEXT = "Vulnerability"
DESCTEXT = "Description"
DATETEXT = "Date"
REVTEXT = "Revision"
LOWTEXT = "low"
MEDTEXT = "medium"
HIGHTEXT = "high"
CHANCETEXT = "Chance"
DMGTEXT = "Impact"
PRODTEXT = "Product(s)"
REFTEXT = "Reference(s)"
ADDDESCTEXT = "Additional Information"
FAQTEXT = "Questions / Remarks"
SOLTEXT = "Possible Solutions / Mitigating Measures"
DISCTEXT = "Disclaimer"
FAQCONTENT = """\n1) FAQ 1\n2) FAQ 2"""
DISCCONTENT = """No guarantees that everything is correct. Put your own disclaimer here."""
HTMLTEMPLATEDIR = "template/"
HTMLHEADER = HTMLTEMPLATEDIR+"header.html"
HTMLCSS = HTMLTEMPLATEDIR+"cssfile.css"
HTMLFOOTER = HTMLTEMPLATEDIR+"footer.html"