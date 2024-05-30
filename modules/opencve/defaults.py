#!/usr/bin/env python3

NAME = "OpenCVE Feed"
CHANNELS = (
    "newsfeed",
)
# Your OpenCVE instance. You may use the public OpenCVE API as well, but
# be aware of rate limits. It is strongly recommended to setup your own
# OpenCVE instance.
URL = "https://<your-opencve-instance-here>"
API = "/api/cve"
# Username and password to connect to the API endpoint.
USERNAME = "<your-opencve-username>"
PASSWORD = "<your-opencve-password>"
ENTRIES = 30
# The AUTOADVISORY feature is really only useful if you are using other
# related bot modules, such as Qualys, and the bot can 'call itself'.
# E.g.: you would need something like '@qualys sw' as the command.
# The bot will append the product name to the command, to tell itself to
# check if any assets are using the product/software/vendor in question.
# True = enabled, False = disabled
AUTOADVISORY = False
# Format: 'channel name': [ 'command1', 'command2', ... ]
ADVISORYCHANS = {
}
# History file used to prevent double-posting.
HISTORY = "history.cache"
# Consider all CVEs with a score above this value. Prevents noise and helps
# focusing on the high/criticals only.
THRESHOLD = 7.0