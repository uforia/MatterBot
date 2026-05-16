"""Discovery + (re)load of matterbot command modules.

Extracted from MattermostManager.__init__ so it is importable and
unit-testable. Behaviour-preserving for the normal module contract; also
fixes the per-module HELP leak and stale-binds-for-removed-modules bugs
(see the PR 1 design spec).
"""
import importlib
import os
import sys


def load_command_table(modulepath, pkg_prefix, existing=None, do_reload=False):
    """Walk `modulepath` for <name>/command.py and build the command table.

    existing : current self.commands (preserve persisted/runtime 'chans', and
               for names already present their 'binds' — mirrors the original
               'if module_name not in self.commands' skip). None on first load.
    do_reload: importlib.reload already-imported submodules instead of plain
               import (picks up on-disk changes). Reload order is
               defaults -> settings -> command, because command.py re-merges
               its deps from sys.modules at import time.

    Returns (commands, binds, report). Never raises for a per-module failure;
    such modules go to report['failed'] and (if previously loaded) keep their
    prior entry.
    """
    existing = existing or {}
    commands = {}
    report = {"added": [], "refreshed": [], "removed": [], "failed": {}}

    # After a `git pull` adds a brand-new command directory, the import
    # system's finder/directory caches can still be stale and a fresh
    # import_module() of the new package may raise ModuleNotFoundError.
    # importlib docs recommend invalidating caches after creating modules
    # that will be imported. Cheap; run it every time.
    importlib.invalidate_caches()

    found = {}
    for root, _dirs, files in os.walk(modulepath):
        if "command.py" in files:
            key = os.path.basename(root).lower()
            if key in found:
                # Two command dirs whose names collide case-insensitively
                # (e.g. Foo/ and foo/) would otherwise silently shadow each
                # other — the operator loses a command they think is loaded.
                # Report it and keep the first one walked.
                report["failed"][key] = (
                    "duplicate command dir (case-insensitive name collision)")
                continue
            found[key] = files

    def _imp(fqname):
        if do_reload and fqname in sys.modules:
            return importlib.reload(sys.modules[fqname])
        return importlib.import_module(fqname)

    for name, files in found.items():
        try:
            defaults = _imp(f"{pkg_prefix}.{name}.defaults")
            override = (_imp(f"{pkg_prefix}.{name}.settings")
                        if "settings.py" in files else None)
            cmd_mod = _imp(f"{pkg_prefix}.{name}.command")

            preserved = (name in existing
                         and existing[name].get("binds") is not None)
            if preserved:
                binds = existing[name]["binds"]
            else:
                cmd_mod.settings.BINDS = None
                cmd_mod.settings.CHANS = None
                if hasattr(defaults, "BINDS"):
                    cmd_mod.settings.BINDS = defaults.BINDS
                if hasattr(defaults, "CHANS"):
                    cmd_mod.settings.CHANS = defaults.CHANS
                if override is not None:
                    if hasattr(override, "BINDS"):
                        cmd_mod.settings.BINDS = override.BINDS
                    if hasattr(override, "CHANS"):
                        cmd_mod.settings.CHANS = override.CHANS
                binds = cmd_mod.settings.BINDS

            if name in existing and "chans" in existing[name]:
                chans = existing[name]["chans"]
            else:
                chans = cmd_mod.settings.CHANS

            help_obj = None
            if hasattr(defaults, "HELP"):
                help_obj = defaults.HELP
            if override is not None and hasattr(override, "HELP"):
                help_obj = override.HELP

            commands[name] = {
                "binds": list(binds) if binds else [],
                "chans": list(chans) if chans else [],
                "process": getattr(cmd_mod, "process"),
                "help": help_obj,
            }
            report["refreshed" if name in existing else "added"].append(name)
        except Exception as exc:  # per-module: never fatal
            report["failed"][name] = repr(exc)
            if name in existing and "process" in existing[name]:
                commands[name] = existing[name]

    for name in existing:
        if name not in found:
            report["removed"].append(name)

    binds = sorted({b for entry in commands.values()
                    for b in (entry["binds"] or [])})
    return commands, binds, report
