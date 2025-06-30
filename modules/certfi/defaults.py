#!/usr/bin/env python3

NAME = "Kyberturvallisuuskeskuksen Suomi (NCSC-FI)"
URLS = (
    "https://www.kyberturvallisuuskeskus.fi/feed/rss/en/399",                   # Newsletter
    "https://www.kyberturvallisuuskeskus.fi/sites/default/files/rss/news.xml"   # External threat intelligence sources
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Generic News",
    "Government",
    "Security Posture"
)
ENTRIES = 10
ADMIN_ONLY = False