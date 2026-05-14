#!/usr/bin/env python3

import logging

log = logging.getLogger("MatterBot")

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path

_pkg = __package__ or Path(__file__).parent.name


def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None


_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here


def process(command, channel, username, params, files, conn):
    messages = []

    if not params:
        return {
            "messages": [
                {"text": "Usage: `@unfurl <URL>` — parses a URL into its components."}
            ]
        }

    url = params[0].strip()
    if not url:
        return {
            "messages": [
                {"text": "Usage: `@unfurl <URL>` — parses a URL into its components."}
            ]
        }

    try:
        # Import lazily so a missing dep produces a clean message rather than
        # crashing module load and taking the whole bot down.
        from unfurl.core import run as unfurl_run

        tree = unfurl_run(
            url,
            data_type="url",
            return_type="text",
            remote_lookups=settings.REMOTE_LOOKUPS,
        )

        if not tree:
            messages.append(
                {"text": f"Unfurl produced no output for `{url}`."}
            )
            return {"messages": messages}

        truncated = False
        if len(tree) > settings.MAX_OUTPUT_CHARS:
            tree = tree[: settings.MAX_OUTPUT_CHARS]
            truncated = True

        body = f"**Unfurl tree for `{url}`:**\n```\n{tree}\n```"
        if truncated:
            body += (
                f"\n_Output truncated at {settings.MAX_OUTPUT_CHARS} characters; "
                "run unfurl locally for the full tree._"
            )

        messages.append({"text": body})
    except ImportError:
        log.warning(
            "unfurl module: dfir-unfurl package not installed; "
            "install with `pip install dfir-unfurl[all]`"
        )
        messages.append(
            {
                "text": "Unfurl is not installed on this host. "
                "Run `pip install dfir-unfurl[all]` and restart the bot."
            }
        )
    except Exception as e:
        log.exception("unfurl module error")
        messages.append(
            {"text": f"An error occurred in Unfurl:\nError: {str(e)}"}
        )

    return {"messages": messages}
