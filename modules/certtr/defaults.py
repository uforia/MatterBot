#!/usr/bin/env python3

NAME = "CERT Türkiye Cumhuriyeti (USOM)"
URL = "https://www.usom.gov.tr/rss/tehdit.rss"      # Security Notifications feed
# "https://www.usom.gov.tr/rss/zararli-baglanti.rss"  # Malicious links feed [Noisy, therefore not standard included]
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Government",
    "Vulnerabilities"
)
ENTRIES = 10
TRANSLATION = True
ADMIN_ONLY = False