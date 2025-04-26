#!/usr/bin/env python3

NAME = "CERT Türkiye Cumhuriyeti (USOM)"
CHANNELS = (
    "newsfeed",
)
URL = "https://www.usom.gov.tr/rss/tehdit.rss"      # Security Notifications feed

"https://www.usom.gov.tr/rss/zararli-baglanti.rss"  # Malicious links feed [Noisy, therefore not standard included]

ENTRIES = 10
TRANSLATION = True