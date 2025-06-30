#!/usr/bin/env python3

NAME = "CERT Republik Österreich"
URLS = (
    "https://www.cert.at/cert-at.de.warnings.rss_2.0.xml",
    "https://www.cert.at/cert-at.de.blog.rss_2.0.xml"
    )
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
ENTRIES = 10
TRANSLATION = True
