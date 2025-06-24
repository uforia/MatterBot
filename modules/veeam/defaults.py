#!/usr/bin/env python3

NAME = "Veeam Advisories"
CHANNELS = (
    "newsfeed",
)
URL = "https://www.veeam.com/kb_rss"
TOPICS = (
    "Advisories",
    "Enterprise Software",
    "Vendor",
    "Vulnerabilities"
)
ENTRIES = 10
FILTER = True # Filter advisories for cvss scores
