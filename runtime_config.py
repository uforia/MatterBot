"""Shared runtime configuration helpers for matterbot and matterfeed.
Dependency-free and importable so it is unit-testable without a live
Mattermost connection.
"""
import logging
import sys

_LOG_FORMAT = "%(levelname)s - %(name)s - %(asctime)s - %(message)s"
_STDOUT_SENTINELS = (None, "", "-")


def configure_logging(matterbot_opts, debug):
    """debug -> DEBUG to stdout (legacy). Else INFO; logfile of None/""/"-"
    -> stdout (journald), otherwise that file (legacy default preserved)."""
    if debug:
        logging.basicConfig(level=logging.DEBUG, format=_LOG_FORMAT, stream=sys.stdout)
        return
    logfile = matterbot_opts.get("logfile")
    if logfile in _STDOUT_SENTINELS:
        logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, stream=sys.stdout)
    else:
        logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, filename=logfile)


def resolve_feedmap(options):
    """Single source of truth for the feedmap path. Matterbot.feedmap wins;
    Modules.feedmap is a deprecated fallback alias. Default 'feedmap.json'."""
    matterbot = getattr(options, "Matterbot", {}) or {}
    if matterbot.get("feedmap"):
        return matterbot["feedmap"]
    modules = getattr(options, "Modules", {}) or {}
    if modules.get("feedmap"):
        return modules["feedmap"]
    return "feedmap.json"
