#!/usr/bin/env python3

NAME = "CERT Centro Criptológico Nacional"
CHANNELS = (
    "newsfeed",
)
URLS = (
    "https://www.ccn-cert.cni.es/es/seguridad-al-dia/alertas-ccn-cert.feed?type=rss", # Alerts
    "https://www.ccn-cert.cni.es/es/seguridad-al-dia/avisos-ccn-cert.html?type=rss"   # Advisories
)
ENTRIES = 10
TRANSLATION = True