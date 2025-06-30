#!/usr/bin/env python3

NAME = "Palo Alto/Unit 42 Advisories"
URLS = (
    "https://security.paloaltonetworks.com/rss.xml",
    "https://unit42.paloaltonetworks.com/feed/"
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "CTI",
    "Vendor",
    "Vulnerabilities"
)
ADMIN_ONLY = False
ENTRIES = 10
