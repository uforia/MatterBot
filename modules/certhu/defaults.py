#!/usr/bin/env python3

NAME = "Nemzeti Koordinációs Központ (NCSC-HU)"
URLS = (
    "https://nki.gov.hu/figyelmeztetesek/tajekoztatas/feed/",   # Security Awareness
    "https://nki.gov.hu/figyelmeztetesek/riasztas/feed/",       # Alerts
    "https://nki.gov.hu/it-biztonsag/hirek/feed/"               # External research
    "https://nki.gov.hu/feed/serulekenysegek",                  # Active Vulnerabilities
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Government",
    "Vulnerabilities"
)
ADMIN_ONLY = False
ENTRIES = 10
TRANSLATION = True
