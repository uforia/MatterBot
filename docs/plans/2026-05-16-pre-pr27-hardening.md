# Pre-PR27 Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Land small, reviewable improvements that prepare MatterBot for PR27 structured output without changing module output behavior yet.

**Architecture:** Start with non-invasive static contract tests and CI, then add framework utility/validation functions, then surface diagnostics through a built-in `health` command. Keep each PR independently useful and backwards compatible.

**Tech Stack:** Python 3 stdlib (`unittest`, `ast`, `pathlib`), GitHub Actions, existing MatterBot command module pattern.

---

## PR 1: Static module contract tests and CI

### Task 1: Add static command/feed contract tests

**Files:**
- Create: `tests/test_module_contracts.py`

**Step 1: Write the static tests**

Create tests that avoid importing command/feed modules, because many integrations require optional system tools, API clients, or local settings. Use `ast` instead.

Checks:
- every `commands/*` directory has `command.py` and `defaults.py`
- every command `command.py` defines `process`
- every command `defaults.py` assigns `HELP`, `BINDS`, and `CHANS`
- every `modules/*` directory has `feed.py` and `defaults.py`
- every feed `feed.py` defines `query`
- every feed `defaults.py` assigns `NAME`

**Step 2: Run tests**

Run: `python3 -m unittest tests.test_module_contracts -v`
Expected: PASS.

**Step 3: Commit**

```bash
git add tests/test_module_contracts.py
git commit -m "test: add static module contract checks"
```

### Task 2: Add CI for stdlib tests

**Files:**
- Create: `.github/workflows/tests.yml`

**Step 1: Add workflow**

Run `python -m unittest discover -s tests -v` on PRs and manual dispatch. Do not install project requirements; these tests must remain dependency-light.

**Step 2: Run locally**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS.

**Step 3: Commit**

```bash
git add .github/workflows/tests.yml
git commit -m "ci: run stdlib tests"
```

---

## PR 2: Response contract validator utilities

### Task 3: Add legacy response validation helper

**Files:**
- Create: `matterbot_contracts.py`
- Create: `tests/test_response_contracts.py`

**Step 1: Write tests first**

Test valid and invalid legacy responses:
- `None` is accepted for no-op modules
- `{'messages': [{'text': 'ok'}]}` is valid
- uploads must be a list of dicts with `filename` and `bytes`
- malformed messages return human-readable errors

**Step 2: Implement helper**

Add:
- `validate_legacy_response(result) -> list[str]`
- `is_valid_legacy_response(result) -> bool`

No behavior change in `matterbot.py` yet.

**Step 3: Run tests and commit**

```bash
python3 -m unittest tests.test_response_contracts -v
git add matterbot_contracts.py tests/test_response_contracts.py
git commit -m "feat: add legacy response contract validator"
```

---

## PR 3: Shared safe formatting helpers

### Task 4: Add IOC/Markdown helper module

**Files:**
- Create: `matterbot_formatting.py`
- Create: `tests/test_formatting.py`

**Step 1: Write tests**

Cover:
- `defang_ioc('example.com', 'domain-name') == 'example[.]com'`
- URL defanging changes `http` to `hxxp` and first dot to `[.]`
- Markdown table cells escape `|` and newlines
- unknown types pass through safely

**Step 2: Implement helpers**

Add:
- `defang_ioc(value, stixtype=None)`
- `safe_markdown_cell(value)`
- `format_scalar(value)`

Do not change existing modules yet.

**Step 3: Run tests and commit**

```bash
python3 -m unittest tests.test_formatting -v
git add matterbot_formatting.py tests/test_formatting.py
git commit -m "feat: add shared formatting helpers"
```

---

## PR 4: Module loading diagnostics groundwork

### Task 5: Record command module load failures

**Files:**
- Modify: `matterbot.py`
- Create: `tests/test_diagnostics.py`

**Step 1: Extract load diagnostics shape**

Add a tiny pure function or dataclass-free dict helper so tests do not need Mattermost.

Diagnostic entry shape:

```python
{
    'kind': 'command',
    'module': 'virustotal',
    'path': 'commands/virustotal/command.py',
    'status': 'ok' | 'error',
    'error': '...'
}
```

**Step 2: Update loading code**

During command discovery, collect failures in `self.module_diagnostics` and continue loading other modules where safe. Keep existing startup behavior for catastrophic config errors.

**Step 3: Run tests and commit**

```bash
python3 -m unittest tests.test_diagnostics -v
git add matterbot.py tests/test_diagnostics.py
git commit -m "feat: collect command module diagnostics"
```

---

## PR 5: `health` command

### Task 6: Add built-in health command

**Files:**
- Modify: `matterbot.py`
- Modify: `config.defaults.yaml`
- Create: `tests/test_health.py`
- Update: `README.md`

**Step 1: Add config commands**

Add default health triggers:

```yaml
healthcmds:
  - "!health"
  - "@health"
```

**Step 2: Add formatter tests**

Test pure function `format_health_report(diagnostics, scope=None)`.

**Step 3: Wire command dispatch**

In `handle_post`, route `@health` before module dispatch. Initial scopes:
- no args: summary
- `commands`: command diagnostics
- `feeds`: static feed count / feedmap availability if loaded

**Step 4: Document usage**

Add short README section near `matterbot.py` commands.

**Step 5: Run tests and commit**

```bash
python3 -m unittest discover -s tests -v
git add matterbot.py config.defaults.yaml tests/test_health.py README.md
git commit -m "feat: add health diagnostics command"
```

---

## PR 6: Optional module risk metadata

### Task 7: Add metadata convention and docs

**Files:**
- Modify: `commands/example/defaults.py`
- Update: `README.md`
- Create: `tests/test_risk_metadata.py`

**Step 1: Add optional `RISK` example**

```python
RISK = {
    'active_network': False,
    'downloads_samples': False,
    'paid_api': False,
    'sends_user_query_to_third_party': False,
}
```

**Step 2: Test metadata shape where present**

Static AST test: if a command defaults file assigns `RISK`, it must be a dict with boolean values.

**Step 3: Document**

Explain that enforcement is future work; this PR only establishes the convention.

**Step 4: Run tests and commit**

```bash
python3 -m unittest discover -s tests -v
git add commands/example/defaults.py README.md tests/test_risk_metadata.py
git commit -m "docs: define optional module risk metadata"
```
