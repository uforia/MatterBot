#!/usr/bin/env python3

import contextlib
import io
import logging
import re

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

# Strict RFC-1123 hostname check — rejects URLs with paths, IPs, and shell
# metacharacters so the operator-supplied string is safe to pass to dnstwist.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)


def _format_results(domain, results, registered_only):
    if not results:
        if registered_only:
            return f"No registered permutations found for `{domain}`."
        return f"No permutations generated for `{domain}`."

    by_fuzzer = {}
    for r in results:
        fuzzer = r.get("fuzzer", "unknown")
        by_fuzzer.setdefault(fuzzer, []).append(r)

    lines = []
    for fuzzer in sorted(by_fuzzer):
        entries = by_fuzzer[fuzzer]
        lines.append(f"\n## {fuzzer} ({len(entries)})")
        for r in entries:
            perm = r.get("domain", "?")
            a = r.get("dns_a") or []
            aaaa = r.get("dns_aaaa") or []
            ns = r.get("dns_ns") or []
            mx = r.get("dns_mx") or []
            extras = []
            if a:
                extras.append("A=" + ",".join(a))
            if aaaa:
                extras.append("AAAA=" + ",".join(aaaa))
            if ns:
                extras.append("NS=" + ",".join(ns))
            if mx:
                extras.append("MX=" + ",".join(mx))
            if extras:
                lines.append(f"  {perm}  [{' | '.join(extras)}]")
            else:
                lines.append(f"  {perm}")

    return "\n".join(lines)


def process(command, channel, username, params, files, conn):
    messages = []

    if not params:
        return {
            "messages": [
                {
                    "text": "Usage: `@dnstwist <domain>` — generates typosquatting permutations of a domain."
                }
            ]
        }

    raw = params[0].strip().lower().strip(".")
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    domain = raw.split("/", 1)[0]

    if not _DOMAIN_RE.match(domain):
        return {
            "messages": [
                {
                    "text": f"`{params[0]}` does not look like a valid domain. Pass a bare hostname like `example.com`."
                }
            ]
        }

    try:
        # Lazy import so a missing dep produces a clean message rather than
        # crashing module load and taking the whole bot down.
        import dnstwist

        kwargs = {"domain": domain, "format": "null"}
        if settings.REMOTE_LOOKUPS:
            kwargs["registered"] = True
            kwargs["threads"] = settings.THREADS

        # dnstwist may emit progress chatter to stdout/stderr; capture it so the
        # bot's logs don't fill up with CLI-style output when called programmatically.
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            results = dnstwist.run(**kwargs)

        if results is None:
            results = []

        truncation_note = ""
        if len(results) > settings.MAX_RESULTS:
            results = results[: settings.MAX_RESULTS]
            truncation_note = (
                f"\n_Result list truncated at {settings.MAX_RESULTS} entries; "
                "run dnstwist locally for the full set._"
            )

        registered_only = bool(settings.REMOTE_LOOKUPS)
        body = _format_results(domain, results, registered_only)

        truncated = False
        if len(body) > settings.MAX_OUTPUT_CHARS:
            body = body[: settings.MAX_OUTPUT_CHARS]
            truncated = True

        mode = (
            "registered permutations"
            if registered_only
            else "permutations (no DNS resolution)"
        )
        wrapped = (
            f"**DNSTwist {mode} for `{domain}`:**\n```\n{body}\n```{truncation_note}"
        )
        if truncated:
            wrapped += (
                f"\n_Output truncated at {settings.MAX_OUTPUT_CHARS} characters._"
            )

        messages.append({"text": wrapped})
    except ImportError:
        log.warning(
            "dnstwist module: dnstwist package not installed; "
            "install with `pip install dnstwist`"
        )
        messages.append(
            {
                "text": "DNSTwist is not installed on this host. "
                "Run `pip install dnstwist` and restart the bot."
            }
        )
    except Exception as e:
        log.exception("dnstwist module error")
        messages.append({"text": f"An error occurred in DNSTwist:\nError: {str(e)}"})

    return {"messages": messages}
