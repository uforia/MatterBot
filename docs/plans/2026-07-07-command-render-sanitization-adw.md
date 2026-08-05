# ADW Spec — Command render-output sanitization

**Status:** Draft · **Date:** 2026-07-07 · **Source:** `/scan adw` deep-scan of MatterBot (Leverage 4 / Automatability 5, top-ranked candidate) · **Build as:** workflow · **SDLC node:** CODE

---

## 1. Why this is worth automating

The single largest churn stream in the repo is markdown-injection sanitization of upstream feed content before Mattermost renders it:

- **116-commit `commands/**` cluster, repoShare 0.55, still active (last touched 55d ago).** By volume it is the dominant thing this repo does.
- Commit stems are uniformly one bug class re-fixed in new places: *neutralise ``` fence breakout*, *strip backticks from heading query echo*, *wrap blockquote text in inline-code*, *sanitise snippet before rendering as blockquote in DM alert*, *escape description blockquote + heading*.
- Every command module in `commands/**` (~50+ integrations: abuseipdb, censys, crtsh, alienvault…) pulls attacker-influenced text from third-party feeds and renders it into Mattermost markdown. Each new integration re-encounters the same escaping bugs → a new one-off commit.

This is a **security workflow** (markdown/format injection from untrusted upstream), not cosmetic formatting. A crafted feed field can break out of a code fence, forge a blockquote, or inject a heading into a DM alert.

## 2. Current state (ground truth, read 2026-07-07)

`matterbot_formatting.py` already exists as the intended convergence point. Its own docstring: *"centralized defanging and Markdown-safe cell formatting … can be adopted by legacy modules gradually."* It currently exposes exactly three helpers:

| Helper | Covers | Gap |
|---|---|---|
| `defang_ioc(value, stixtype)` | IOC defanging (first-dot, hxxp) | — |
| `safe_markdown_cell(value)` | table cells: `\|`, `\r`, `\n` | **only table context** |
| `format_scalar(value, stixtype)` | defang → cell → backtick-wrap | inline scalar only |

`tests/test_formatting.py` (44 lines, `unittest`) covers those three and nothing else.

**The gap that generates the 116 commits:** there is **no centralized sanitizer** for the injection vectors the commits keep fixing inline —

1. **Code-fence breakout** — ` ``` ` appearing inside content rendered into a fenced block (the #1 stem).
2. **Blockquote injection** — a leading `>` on any line forging quote structure in DM alerts.
3. **Heading injection** — a leading `#` echoing a user query as an `<h1>`.
4. **Inline-backtick neutralization** — stray backticks breaking inline-code wrapping.

Because these live inline in each command module, every new module re-discovers them. That is the toil this ADW eliminates.

## 3. The workflow

A three-phase, re-runnable workflow. Each phase gated by `pytest tests/test_formatting.py`.

### Phase A — Centralize the missing sanitizers (one-time, then stable)
Add to `matterbot_formatting.py`, matching the existing dependency-free / `None`-safe / str-coercing style:

- `sanitize_block(value)` — content destined for a fenced code block: neutralize ` ``` ` sequences (e.g. zero-width or backslash break), strip trailing control chars.
- `sanitize_blockquote(value)` — escape leading `>` per line so upstream text cannot forge quote structure.
- `sanitize_inline(value)` — content destined for inline-code: strip/escape backticks so the `` ` `` wrapper cannot be broken (generalizes what `format_scalar` assumes).
- `sanitize_heading_echo(value)` — escape leading `#`/`>` when echoing a user query into a header.

Each new helper ships **with its test cases** in `tests/test_formatting.py` (adversarial inputs, not just happy path — see Phase C).

### Phase B — Detect unsanitized render sites (the automatable audit)
A detector pass over `commands/**` that flags render sites emitting upstream text without routing through a `matterbot_formatting` helper. Heuristics (metadata/AST, not runtime):

- f-strings / `.format` / concatenation that interpolate feed-derived variables directly into a string containing ` ``` `, a leading `>`, `#`, or `` ` `` wrapper.
- Any `commands/*/` module that imports none of the sanitizers but writes to a message/blockquote/fenced field.

Output: ranked list of `commands/<name>` sites + the vector each is exposed to. This is the worklist for Phase C.

### Phase C — Codemod adoption + property tests (the repeatable per-module loop)
For each flagged module:
1. Route its render path through the correct `matterbot_formatting` helper (mechanical: wrap the interpolated value).
2. Add/extend a **property test** in `tests/test_formatting.py` feeding adversarial payloads (` ```injected ```, `>forged`, `#h1`, `` `broken`` ) through the module's render path and asserting the output cannot break out.
3. Gate: `pytest tests/test_formatting.py` green → module done.

Idempotent: already-sanitized modules are skipped by the Phase B detector, so the workflow converges and can be re-run as new integrations land.

## 4. Validation loop

```
pytest tests/test_formatting.py
```

Deterministic, already wired in `tests.yml` CI. The `f821-delta.yml` (pyflakes undefined-name) gate stays green as a secondary guard on the codemod. **No candidate site is closed until the formatting test proves the specific breakout is neutralized** — the test is the definition of done, per phase.

## 5. Scope / non-goals

- **In:** markdown-injection sanitization of upstream content in `commands/**` render paths; centralization into `matterbot_formatting.py`; property-test coverage.
- **Out — do NOT bundle:**
  - Core dispatch / ACL / bare-except hardening (`matterbot.py` cluster) — separate concern, apex-hunter territory, its own ADW candidate.
  - Feed fetch/parse correctness (`modules/**`) — blocked on a feed smoke test that does not yet exist (Fix-first item from the scan).
  - The PR27 structured renderer itself — this ADW feeds it (adopts the helpers) but does not build it.

## 6. Blast radius & risks

- **Touches many files** (`commands/**`, avg 8 files/commit historically) but each change is mechanical and individually test-gated → bounded by `test_formatting.py`.
- **Behavioral risk:** over-escaping could double-escape already-safe content. Mitigation: property tests assert *round-trip readability* on benign inputs alongside breakout-prevention on hostile ones (mirror the existing `test_unknown_type_passes_through` style).
- **Adoption drift:** new command modules can regress. Mitigation: the Phase B detector can run in CI as a lint (fail if a `commands/*` render site bypasses the sanitizers) — converts the ADW's audit into a standing guardrail.

## 7. Suggested build target

A `workflow` (Phase B detector + Phase C codemod loop), with the Phase A helpers landed first as a normal PR. The Phase B detector is the reusable asset — it is what makes this recurring toil converge instead of recurring forever.
