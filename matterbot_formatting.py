"""Shared formatting helpers for MatterBot output.

The PR27 structured renderer will need centralized defanging and Markdown-safe
cell formatting. These helpers are dependency-free and can be adopted by legacy
modules gradually before the renderer lands.
"""


def defang_ioc(value, stixtype=None):
    """Return a safely defanged IOC string for known semantic types.

    Only the first dot is replaced to preserve readability and to match the
    defanging convention already used in the PR27 proposal. Unknown types are
    returned unchanged as strings.
    """
    if value is None:
        return ""

    text = str(value)
    if stixtype in ("ipv4-addr", "ipv6-addr", "domain-name"):
        return text.replace(".", "[.]", 1)
    if stixtype == "url":
        if text.startswith("https"):
            text = "hxxps" + text[5:]
        elif text.startswith("http"):
            text = "hxxp" + text[4:]
        return text.replace(".", "[.]", 1)
    return text


def safe_markdown_cell(value):
    """Return text safe to place inside a Markdown table cell."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def format_scalar(value, stixtype=None):
    """Format a scalar value for Mattermost Markdown output."""
    text = safe_markdown_cell(defang_ioc(value, stixtype))
    if not text:
        return "-"
    return f"`{text}`"
