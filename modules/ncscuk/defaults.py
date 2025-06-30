#!/usr/bin/env python3

NAME = "NCSC-UK Advisories"
URL = "https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml"
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
