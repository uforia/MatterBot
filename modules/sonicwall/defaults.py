#!/usr/bin/env python3

NAME = "Sonicwall Advisories"
URL = "https://psirtapi.global.sonicwall.com/api/v1/feed/rss.xml"
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Vendor",
    "Vulnerabilities",
)
ADMIN_ONLY = False
ENTRIES = 10
