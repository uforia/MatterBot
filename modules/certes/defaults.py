#!/usr/bin/env python3

NAME = "CERT Instituto Nacional de Ciberseguridad"
# And Centro Criptológico Nacional
URLS = (
    "https://www.incibe.es/en/incibe-cert/blog/feed/",                                 # CERT Blog
    "https://www.incibe.es/incibe-cert/alerta-temprana/avisos-sci/feed",               # CERT ICS Advisories
    "https://www.incibe.es/incibe-cert/alerta-temprana/avisos/feed",                   # CERT Advisories
    "https://www.incibe.es/incibe-cert/alerta-temprana/vulnerabilidades/feed",         # CERT Vulnerabilities
    "https://www.incibe.es/en/incibe-cert/publications/cybersecurity-highlights/feed", # CERT Cybersecurity Highlights (Based off external research)
    "https://www.ccn-cert.cni.es/es/seguridad-al-dia/alertas-ccn-cert.feed?type=rss",  # CCNI Alerts
    "https://www.ccn-cert.cni.es/es/seguridad-al-dia/avisos-ccn-cert.html?type=rss"    # CCNI Advisories
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Government",
    "Threat Intelligence",
    "Vulnerabilities"
)
ENTRIES = 10
TRANSLATION = True
ADMIN_ONLY = False