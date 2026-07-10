#!/usr/bin/env python3
"""Static contract check for feed modules.

`matterfeed.callModule` loads each `modules/<name>/feed.py` and calls its
top-level `query` function; settings come from `defaults.py` (optionally
overridden by `settings.py`). A module that is missing that entry point, has a
syntax error, or lacks `defaults.py` fails silently at runtime — the feed just
goes quiet with no operational signal.

This checker enforces that contract statically (AST only), so it needs none of
the feeds' third-party dependencies and is safe to run in CI. It is a load
contract, not a fetch test: it does not hit the network or execute module code.

Usage:
    python3 feed_audit.py [--check] [--root modules]
"""

import argparse
import ast
import sys
from pathlib import Path

ENTRY_POINT = "query"


def _has_top_level_function(tree, name):
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        for node in tree.body
    )


def _has_top_level_assignment(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return True
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                return True
    return False


def check_feed_module(module_dir):
    """Return a list of contract-violation strings for one module dir (empty = OK)."""
    module_dir = Path(module_dir)
    violations = []

    feed_py = module_dir / "feed.py"
    if not feed_py.is_file():
        violations.append("missing feed.py")
    else:
        try:
            tree = ast.parse(feed_py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            violations.append(f"feed.py has a syntax error at line {e.lineno}: {e.msg}")
        else:
            if not _has_top_level_function(tree, ENTRY_POINT):
                violations.append(f"feed.py defines no top-level {ENTRY_POINT}() entry point")

    defaults_py = module_dir / "defaults.py"
    if not defaults_py.is_file():
        violations.append("missing defaults.py")
    else:
        try:
            defaults_tree = ast.parse(defaults_py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            violations.append(f"defaults.py has a syntax error at line {e.lineno}: {e.msg}")
        else:
            if not _has_top_level_assignment(defaults_tree, "NAME"):
                violations.append("defaults.py does not define NAME (matterfeed reads settings.NAME unconditionally)")

    return violations


def iter_feed_module_dirs(root):
    """Yield each candidate feed-module directory under root (skips dotdirs / dunders)."""
    root = Path(root)
    for child in sorted(root.iterdir()):
        if child.is_dir() and not child.name.startswith((".", "_")):
            yield child


def audit_feed_modules(root="modules"):
    """Return {module_name: [violations]} for every module that violates the contract."""
    result = {}
    for module_dir in iter_feed_module_dirs(root):
        violations = check_feed_module(module_dir)
        if violations:
            result[module_dir.name] = violations
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Static contract check for feed modules.")
    parser.add_argument("--root", default="modules", help="modules directory to scan (default: modules)")
    parser.add_argument("--check", action="store_true", help="exit non-zero if any violations (CI gate mode)")
    args = parser.parse_args(argv)

    violations = audit_feed_modules(args.root)
    if not violations:
        print("feed_audit: all feed modules satisfy the load contract.")
        return 0

    print(f"feed_audit: {len(violations)} module(s) violate the load contract:")
    for module in sorted(violations):
        for v in violations[module]:
            print(f"  {module}: {v}")
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
