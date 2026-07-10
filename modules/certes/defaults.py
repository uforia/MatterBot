#!/usr/bin/env python3

NAME = "CERT Instituto Nacional de Ciberseguridad"
# And Centro Criptológico Nacional
URLS = (
    "https://www.incibe.es/en/incibe-cert/blog/feed/",                                 # CERT Blog
    "https://www.incibe.es/incibe-cert/alerta-temprana/avisos-sci/feed",               # CERT ICS Advisories
    "https://www.incibe.es/incibe-cert/alerta-temprana/avisos/feed",                   # CERT Advisories
    "https://www.incibe.es/incibe-cert/alerta-temprana/vulnerabilidades/feed",         # CERT Vulnerabilities
    "https://www.incibe.es/en/incibe-cert/publications/cybersecurity-highlights/feed", # CERT Cybersecurity Highlights (Based off external research)
    # CCN-CERT (ccn-cert.cni.es) feeds removed: the site serves an HTTP 403
    # "Voight-Kampff" anti-bot challenge to automated fetchers, so these never
    # yield data and their block page can crash the feed parse (see feed.py).
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Government",
    "CTI",
    "Vulnerabilities"
)
ADMIN_ONLY = False
ENTRIES = 10
TRANSLATION = True
