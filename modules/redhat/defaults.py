#!/usr/bin/env python3

NAME = "Red Hat Product Advisories"
URL = "https://access.redhat.com/security/data/meta/v1/rhsa.rss"
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "CTI",
    "Software",
    "Vulnerabilities"
)
ADMIN_ONLY = False
ENTRIES = 10
