#!/usr/bin/env python3

NAME = "Veeam Advisories"
URL = "https://www.veeam.com/kb_rss"
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Software",
    "Vendor",
    "Vulnerabilities"
)
ADMIN_ONLY = False
ENTRIES = 10
FILTER = True # Filter advisories for cvss scores
