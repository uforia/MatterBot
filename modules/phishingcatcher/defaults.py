#!/usr/bin/env python3

NAME = "PhishingCatcher"
CHANNELS = (
    "newsfeed",
)
SUSLOG = "suspicious_domains.log" # Can be a URL, e.g. http(s)://[..]example.com/suspicious_domains.log
AUTH = { # Can be used for HTTP(S) AUTH
    'username': '<user>',
    'password': '<pass>',
}
DOMAINS = ( # Use '.' for a wildcard: all domains contain at least one '.'
    'example.com',
    'your-companys-domain-here.com',
)
HISTORY = 'history.cache'
THRESHOLD = 70 # Minimum score before reporting on a domain. Too low: lots of noise. Too high: chance of false negatives.
ENTRIES = 10
