#!/usr/bin/env python3

BINDS = ["@holehe"]
CHANS = ["debug"]

# Holehe checks if an email is registered against ~120 services by triggering
# their password-reset / signup-collision flows. That is a meaningful amount of
# outbound traffic per query and can occasionally trip rate limits on the
# target services. Operators who want to point this at sensitive addresses
# should think about whether they are comfortable making that visible to those
# services.
#
# Default timeout for the holehe subprocess in seconds. The full check sweep
# can take 30s+ on a cold network; lower this if you only want fast services.
TIMEOUT = 60

# Soft cap on the rendered message body. Mattermost rejects very large
# messages; anything above this is truncated with a footer note instead of
# being silently dropped.
MAX_OUTPUT_CHARS = 6000

HELP = {
    "DEFAULT": {
        "args": "<email>",
        "desc": "Checks an email address against ~120 online services using "
        "Holehe (https://github.com/megadose/holehe) and reports where the "
        "address is already registered. Useful for account-discovery triage "
        "and account-takeover risk assessment. "
        "Example: `@holehe target@example.com`",
    },
}
