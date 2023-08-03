#!/usr/bin/env python3

NAME = "THOR Parser"
CHANNELS = (
    "debug",
)
MAILSERVER = {
    'hostname': '<something>',
    'username': '<username>',
    'password': '<password>',
}
SFTPSERVER = {
    'hostname': '<something>',
    'port': 22,
    'username': '<username>',
    'password': '<password>',
    'incoming': '/upload',
    'archive': '/archive',
}
# Set threshold for warning/alerts. THOR's subscore calculations differ per version, see:
# https://thor-manual.nextron-systems.com/en/latest/usage/other-topics.html#scoring-system
THOR = {
    'md5s': 'md5s.csv',
    'subscore_threshold': 95,
    'subscore_low': 95,
    'subscore_medium': 140,
    'subscore_high': 180,
}
ENTRIES = 100
