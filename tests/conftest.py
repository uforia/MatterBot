import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Make `import matterbot` resilient to a test interpreter that lacks the
# heavy runtime deps (configargparse, mattermostdriver). Tests that only
# exercise pure logic (format_reload_report, etc.) must not require the
# full deployment stack to be pip-installed for whatever Python pytest
# happens to run under. Real modules are preferred; a stub is installed
# only when the real one is absent.
for _dep in ("configargparse",):
    try:
        __import__(_dep)
    except ModuleNotFoundError:
        sys.modules[_dep] = types.ModuleType(_dep)

try:
    __import__("mattermostdriver")
except ModuleNotFoundError:
    _mm = types.ModuleType("mattermostdriver")
    _mm.Driver = object
    sys.modules["mattermostdriver"] = _mm
