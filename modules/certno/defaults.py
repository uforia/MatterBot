#!/usr/bin/env python3

NAME = "Nasjonal sikkerhetsmyndighet (NorCERT)"
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Generic News",
    "Government",
    "Vulnerabilities"
)
ADMIN_ONLY = False
URL = "https://nsm.no/rss/alle-oppdateringer-fra-nsm/"
ENTRIES = 10
TRANSLATION = True
