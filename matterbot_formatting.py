"""Shared formatting helpers for MatterBot output.

The PR27 structured renderer will need centralized defanging and Markdown-safe
cell formatting. These helpers are dependency-free and can be adopted by legacy
modules gradually before the renderer lands.

The ``sanitize_*`` helpers neutralize Markdown-injection vectors in
attacker-influenced upstream feed content before it is rendered into a
Mattermost message. They centralize escaping logic that was previously
re-implemented inline across ``commands/**``.
"""

import re

# Zero-width space: interposed between adjacent backticks so a run cannot close
# a ``` code fence, while keeping the visible backtick count intact.
_ZWSP = chr(0x200B)


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


def sanitize_inline(value):
    """Return text safe to place inside inline-code (single-backtick) wrapping.

    Strips backticks so upstream content cannot break out of the wrapper, and
    collapses newlines so the text stays on one line.
    """
    if value is None:
        return ""
    return str(value).replace("`", "").replace("\r", " ").replace("\n", " ")


def sanitize_block(value):
    """Return text safe to embed inside a fenced (```) code block.

    Interposes a zero-width space between adjacent backticks so no run of
    backticks in the content can close the surrounding fence. The visible
    backtick count is preserved.
    """
    if value is None:
        return ""
    return re.sub(r"`(?=`)", "`" + _ZWSP, str(value))


def sanitize_blockquote(value):
    """Escape a leading ``>`` on each line so upstream text cannot forge a
    blockquote. Leading indentation is preserved."""
    if value is None:
        return ""
    out = []
    for line in str(value).split("\n"):
        stripped = line.lstrip(" ")
        if stripped.startswith(">"):
            indent = line[: len(line) - len(stripped)]
            out.append(indent + "\\" + stripped)
        else:
            out.append(line)
    return "\n".join(out)


def sanitize_heading_echo(value):
    """Return a single-line value safe to echo into a heading.

    Collapses newlines and escapes a leading ``#`` or ``>`` so an echoed user
    query cannot forge a heading or blockquote.
    """
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    stripped = text.lstrip(" ")
    if stripped[:1] in ("#", ">"):
        indent = text[: len(text) - len(stripped)]
        return indent + "\\" + stripped
    return text
