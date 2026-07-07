#!/usr/bin/env python3
"""Audit command modules for unsanitized Markdown render sites.

Command modules render upstream feed content into Mattermost markdown. When that
content is interpolated straight into a markdown-significant context — a ``` code
fence, an inline-code (`) wrap, or a hand-rolled ``stripchars`` filter — attacker
influenced text can break out (fence breakout, forged blockquote/heading).

This is a heuristic, line-based detector: it produces a worklist of sites that
should adopt the ``matterbot_formatting.sanitize_*`` helpers, and (with --check)
can run as a CI lint. It is intentionally conservative and reports rather than
proves; a site already routed through a ``sanitize_*`` helper is treated as safe.

Usage:
    python3 render_audit.py [--check] [--root commands]
"""

import argparse
import re
import sys
from collections import Counter, namedtuple
from pathlib import Path

Finding = namedtuple("Finding", ["module", "line", "vector", "snippet"])

VECTORS = ("fence", "inline", "adhoc-stripchars")

_FENCE = "```"
# An interpolation marker on the same line: %-formatting, str.format, f-string
# placeholder, or a `` % `` expression.
_INTERP = re.compile(r"%[sdr(]|\.format\(|\{|\s%\s")
# Inline-code wrap directly around interpolated content: `{...} or `%s.
_INLINE = re.compile(r"`\{|`%[sdr(]")


def audit_source(source, module):
    """Return a list of Finding for a single module's source text."""
    findings = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if "sanitize_" in line:
            # Already routed through a sanitizer — treat as safe.
            continue
        if _FENCE in line and _INTERP.search(line):
            findings.append(Finding(module, lineno, "fence", line.strip()))
        elif _INLINE.search(line):
            findings.append(Finding(module, lineno, "inline", line.strip()))
        elif "stripchars" in line:
            findings.append(Finding(module, lineno, "adhoc-stripchars", line.strip()))
    return findings


def audit_modules(items):
    """Flatten audit_source over an iterable of (module, source) pairs."""
    findings = []
    for module, source in items:
        findings.extend(audit_source(source, module))
    return findings


def select_vectors(findings, vectors):
    """Keep only findings whose vector is in `vectors`."""
    wanted = set(vectors)
    return [f for f in findings if f.vector in wanted]


def iter_command_sources(root):
    """Yield (module, source) for each commands/<name>/command.py under root."""
    root = Path(root)
    for command_py in sorted(root.glob("*/command.py")):
        module = command_py.parent.name
        yield module, command_py.read_text(encoding="utf-8", errors="replace")


_FIX = {
    "fence": "wrap fenced content in matterbot_formatting.sanitize_block()",
    "inline": "wrap inline-code content in matterbot_formatting.sanitize_inline()",
    "adhoc-stripchars": "replace the ad-hoc stripchars filter with the sanitize_* helpers",
}


def format_report(findings):
    """Render findings as a human-readable worklist grouped by module."""
    if not findings:
        return "render_audit: no unsanitized render sites found."

    by_vector = Counter(f.vector for f in findings)
    modules = sorted({f.module for f in findings})
    lines = [
        f"render_audit: {len(findings)} finding(s) across {len(modules)} module(s)",
        "  by vector: " + ", ".join(f"{v}={n}" for v, n in sorted(by_vector.items())),
        "",
    ]
    current = None
    for f in sorted(findings, key=lambda f: (f.module, f.line)):
        if f.module != current:
            current = f.module
            lines.append(f"{f.module}:")
        lines.append(f"  L{f.line} [{f.vector}] {f.snippet}")
        lines.append(f"      -> {_FIX[f.vector]}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit command modules for unsanitized render sites.")
    parser.add_argument("--root", default="commands", help="commands directory to scan (default: commands)")
    parser.add_argument("--check", action="store_true", help="exit non-zero if any findings (CI lint mode)")
    parser.add_argument(
        "--vectors",
        default=",".join(VECTORS),
        help=f"comma-separated vectors to report/gate on (default: all). Choices: {', '.join(VECTORS)}",
    )
    args = parser.parse_args(argv)

    vectors = [v.strip() for v in args.vectors.split(",") if v.strip()]
    unknown = [v for v in vectors if v not in VECTORS]
    if unknown:
        parser.error(f"unknown vector(s): {', '.join(unknown)}. Choices: {', '.join(VECTORS)}")

    findings = select_vectors(audit_modules(iter_command_sources(args.root)), vectors)
    print(format_report(findings))
    if args.check and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
