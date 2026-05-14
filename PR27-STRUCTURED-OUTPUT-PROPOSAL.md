# PR #27 — Structured Module Output: Implementation Plan

Draft proposal for landing TTycho's "Standard message format" idea as a real, mergeable change rather than the half-feature PR #27 currently is.

## Context — why this isn't just a merge-as-is

PR #27 ([uforia/MatterBot#27](https://github.com/uforia/MatterBot/pull/27)) sketches a structured-data return shape for one module (`cyberthreat`). The idea is sound for a CTI bot: modules return semantic data, the framework renders. That centralizes defanging, enables non-Markdown sinks later (MISP / OpenCTI push, JSON export), and replaces 50 modules each rolling their own Markdown.

What's missing in #27 as it stands:

1. **No renderer.** The PoC module does `return data` and nothing in `matterbot.py` knows how to render the structured dict into a Mattermost message. As written, the bot would silently send nothing to the channel.
2. **Only one module.** No proof the schema generalizes.
3. **No migration story.** The other ~50 modules still return `{'messages': [{'text': '...'}]}`. The framework would need to accept both shapes during a transition.
4. **Indexing bug in the PoC.** Each iteration writes `data['responses'][0]['paragraph']` — always slot 0 — so multi-result queries overwrite earlier sections instead of appending.
5. **Schema gaps.** No file uploads, no thread routing, no render hint, ambiguity between "table of records" and "single key-value record".

This document fills those in.

## Schema spec — v2 (proposed, supersedes #27's sketch)

Modules optionally return:

```python
{
    # Required: name shown in the response header
    "source": "cyberthreat hosting intelligence",

    # Required: list of one-or-more logical sections
    "responses": [
        {
            # Section heading (rendered as level-2 markdown header)
            "paragraph": "IP Lookup",

            # Optional human intro rendered before the data block
            "preamble": "IPv4 address `1.2.3.4` is high-confidence used by **APT-foo**.",

            # List of records. Each record is one row in a table OR one
            # named-fields block in a list. Schema fix for #27's flat
            # data[] which couldn't represent multi-row tables.
            "records": [
                {
                    "category": "Indicator",
                    "fields": [
                        {"name": "IPv4 address", "stixtype": "ipv4-addr",         "value": "1.2.3.4"},
                        {"name": "Last seen",    "stixtype": "x-mb:date",         "value": "2026-05-13"},
                        {"name": "Actor",        "stixtype": "intrusion-set",     "value": "APT-foo"},
                        {"name": "Credibility",  "stixtype": "x-mb:confidence",   "value": "high"},
                    ]
                },
                # ... additional records (e.g. more IPs in the same lookup)
            ],

            # Optional render hint. Auto-detects 'table' if records share
            # the same field shape and len > 1; else 'list'. Override with
            # 'table' | 'list' | 'kv' when the heuristic guesses wrong.
            "render": "table"
        },
        # ... additional responses (different sections)
    ],

    # Optional file uploads (same shape as the current 'uploads' field on
    # legacy messages). Same channel-attachment path under the hood.
    "uploads": [
        {"filename": "report.pdf", "bytes": b"..."}
    ],

    # Optional: post in a thread under the invoking command rather than
    # the main channel timeline.
    "thread": True
}
```

### `stixtype` vocabulary

- **STIX2 SCO names** (`ipv4-addr`, `ipv6-addr`, `domain-name`, `url`, `file:hashes.SHA-256`, `email-addr`, `mutex`, etc.) — drive defanging and presentation. The renderer has a switch on `stixtype` for the special-cased ones.
- **STIX2 SDO names** (`intrusion-set`, `malware`, `tool`, `campaign`, `vulnerability`) — used for actor/family references; render as bold + link if a `details` URL is provided.
- **`x-mb:` extension prefix** for non-STIX semantic types we still want centralized formatting for: `x-mb:date`, `x-mb:confidence`, `x-mb:count`, `x-mb:percent`. Loose vocabulary — unknown types fall through to default backtick formatting, never error.
- **Empty string / missing**: default formatting (`` `value` ``).

## Framework renderer — sketch

Lives in `matterbot.py` (alongside `call_module` / `send_message`). Detects the new shape by the presence of `responses` at the top level; legacy `messages`-shaped returns pass through untouched.

```python
def _render_structured(result: dict) -> dict:
    """Convert a structured module return to legacy {messages: [...]} shape.
    Modules that return the legacy shape pass through unchanged."""
    if 'responses' not in result:
        return result

    parts = []
    if 'source' in result:
        parts.append(f"_{result['source']}_")

    for response in result['responses']:
        if 'paragraph' in response:
            parts.append(f"\n## {response['paragraph']}")
        if 'preamble' in response:
            parts.append(response['preamble'])
        if 'records' in response and response['records']:
            parts.append(_render_records(response['records'], response.get('render')))

    message = {'text': '\n\n'.join(parts)}
    if 'uploads' in result:
        message['uploads'] = result['uploads']

    out = {'messages': [message]}
    if result.get('thread'):
        out['thread'] = True  # call_module honors this for root_id
    return out


def _render_records(records: list, hint: str | None) -> str:
    if hint is None:
        first_fields = [f['name'] for f in records[0].get('fields', [])]
        same_shape = all(
            [f['name'] for f in r.get('fields', [])] == first_fields
            for r in records
        )
        hint = 'table' if (same_shape and len(records) > 1) else 'list'

    if hint == 'table':
        return _render_table(records)
    if hint == 'kv':
        return _render_kv(records)
    return _render_list(records)


def _render_table(records: list) -> str:
    headers = [f['name'] for f in records[0]['fields']]
    lines = ['| ' + ' | '.join(headers) + ' |',
             '| ' + ' | '.join([':-'] * len(headers)) + ' |']
    for r in records:
        cells = [_format_field(f) for f in r['fields']]
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def _render_list(records: list) -> str:
    lines = []
    for i, r in enumerate(records):
        for f in r.get('fields', []):
            lines.append(f"- **{f['name']}**: {_format_field(f)}")
        if i < len(records) - 1:
            lines.append('')
    return '\n'.join(lines)


def _render_kv(records: list) -> str:
    # Single record rendered as a 2-column key-value table
    fields = records[0]['fields']
    lines = ['| Field | Value |', '| :- | :- |']
    for f in fields:
        lines.append(f"| **{f['name']}** | {_format_field(f)} |")
    return '\n'.join(lines)


# Centralized defanging and presentation. This is the real win — every
# IPv4-addr / domain-name / URL is now defanged uniformly instead of
# every module doing its own .replace('.','[.]',1).
def _format_field(field: dict) -> str:
    value = str(field.get('value', ''))
    stixtype = field.get('stixtype', '')

    if stixtype in ('ipv4-addr', 'ipv6-addr', 'domain-name'):
        return '`' + value.replace('.', '[.]', 1) + '`'
    if stixtype == 'url':
        v = value.replace('.', '[.]', 1).replace('http', 'hxxp', 1)
        return '`' + v + '`'
    if stixtype.startswith('file:hashes.'):
        return '`' + value + '`'
    if stixtype == 'x-mb:confidence':
        # Optional emoji/icon enhancement — keep simple for v1
        return value
    if stixtype == 'x-mb:date':
        return f"`{value}`"

    # Default formatting for unknown stixtype / no stixtype set
    return '`' + value + '`' if value else '-'
```

**Integration in `call_module`** (one branch, immediately after the executor returns):

```python
result = await loop.run_in_executor(
    self._command_executor,
    self.commands[module]['process'],
    command, channame, username, params, files, conn,
)
if isinstance(result, dict) and 'responses' in result:
    result = _render_structured(result)
# ... existing 'messages' loop ...
```

## Backwards compatibility — both shapes, indefinitely

The framework accepts both return shapes forever (or until an explicit deprecation milestone). Legacy modules don't need to change. New modules opt in by returning the structured dict. There is **no hard cutover.**

Detection: presence of `responses` at the top level of the return dict.

This means we can:
1. Ship the renderer in `matterbot.py` without touching any module.
2. Pilot-port 3–5 modules to validate the schema.
3. Iterate on the schema based on what the pilots surface.
4. Mass-port at our pace, or never, or selectively.

## Pilot module choices (5 modules, ~3 days of work)

Picked to cover the diversity of existing output shapes:

| Module | Why it's a pilot |
|---|---|
| `cyberthreat` | TTycho's original pilot. IP/domain lookups. Validates the basic shape. |
| `virustotal` | Multi-section output (file info, scan stats, AV detections), large tables, optional images. Validates `responses[]` repetition + `render: table`. |
| `urlscan` | Multi-result table with screenshots in `uploads`. Validates the upload field round-trip. |
| `alienvault` | Multi-endpoint fan-out (already parallelized in #158). Each endpoint becomes one `response`. Validates per-section error handling. |
| `mwdb` | Mixed file/blob/config records + binary uploads. Validates heterogeneous record types in one response. |

Each pilot also surfaces what the centralized defanger handles vs. what the module still needs to render inline.

## Migration plan post-pilot

Once the pilots validate the schema:

1. **Catalog the legacy modules** — group by output shape (table-only, list-only, single-record-kv, mixed, has-uploads, has-images, has-multi-section).
2. **Build a one-shot port script** for the simplest shapes (single-table modules). Probably ~40% of the modules. Hand-review each script-generated port before commit; no blind sed.
3. **Hand-port the irregular ones** — anything that builds Markdown with custom escaping, ASCII art, or non-table layouts. Probably ~20 modules.
4. **Walk away from the rest** — the lols-of-loot modules (`lolbas`, `loldrivers`, `lolrmm`, `loobins`, `gtfobins`) walk a cached JSON dict to print one or two columns. They work fine in the legacy shape; porting them is busy-work with no win. Mark as "legacy stable" and stop touching them.

## Risks / open questions before starting

1. **Non-tabular output**: paragraphs of prose, embedded images, mermaid diagrams. The schema currently has `preamble` for prose; an `html` or `raw_markdown` escape hatch may be needed for the irregular cases. **Decision: add `"raw_markdown": "..."` field at the `response` level as the escape valve.**

2. **STIX vs. arbitrary types**: should `stixtype` strictly enforce STIX2 SDO/SCO/SRO names, or accept anything? **Decision: loose match. Special-case the known names for centralized formatting, fall through to default for anything else. No errors on unknown types.**

3. **Thread routing**: existing `call_module` posts to channel via `send_message(chanid, ..., rootid)`. The structured shape's `"thread": True` would set `rootid` to the invoking post's id. **Decision: support, default off (preserves current behavior).**

4. **JSON / non-Markdown sinks**: should the renderer output JSON for MISP/OpenCTI push? **Decision: out of scope for v1. The renderer always produces Markdown for Mattermost. JSON serialization for downstream sinks is a separate orchestrator concern — the structured shape is already JSON, so a future MISP-push agent can consume the same module return directly.**

5. **Deprecation of legacy shape**: when do we delete the legacy code path? **Decision: don't, for v1. The cost of carrying both code paths is ~50 lines in `matterbot.py`. The risk of a hard cutover is much higher.**

6. **TTycho's PoC bug fix**: do we land the structured shape with the `[0]` indexing bug preserved (for posterity) or fixed (so the cyberthreat pilot actually works)? **Decision: fix it. The bug shipped in a PR that never merged, so there's no "previous behavior" to preserve.**

7. **Test coverage**: matterbot has no test suite. Should this PR add one? **Decision: minimal — a single `tests/test_renderer.py` covering the renderer's table/list/kv shapes + the legacy-passthrough case. Not full bot integration tests. ~50 LoC.**

## Effort estimate

| Phase | Effort |
|---|---|
| Schema spec writeup + review | 0.5 day |
| Renderer in `matterbot.py` + minimal unit tests | 1–2 days |
| Pilot port: `cyberthreat` (TTycho's module) | 0.5 day |
| Pilot port: `virustotal` (validates large-table + multi-section) | 1 day |
| Pilot port: `urlscan` (validates uploads + screenshots) | 0.5 day |
| Pilot port: `alienvault` (validates multi-endpoint fan-out) | 1 day |
| Pilot port: `mwdb` (validates heterogeneous records + binary uploads) | 1 day |
| Schema iteration after pilots surface edge cases | 1–2 days |
| Migration helper script (for the mechanically-portable shape) | 2 days |
| Mass-port + review | 3–5 days |
| **Total** | **~2–3 weeks of focused work** |

## Recommended PR sequence

1. **PR A**: Schema doc + renderer + renderer unit tests + framework-passthrough detection. No module changes. Easy to review and revert.
2. **PR B**: `cyberthreat` pilot port. Smallest pilot. Validates the renderer end-to-end against real bot output.
3. **PR C**: `virustotal` + `urlscan` + `alienvault` + `mwdb` ports. Four pilots together so reviewer can compare.
4. **PR D**: Iteration patch — fixes whatever the pilots surface (likely new `stixtype` cases, `render` hint refinements, edge cases in `_format_field`).
5. **PRs E…N**: Mass-port, one PR per ~5 modules. Stop whenever the remaining modules don't deserve the work.

## What to do with #27 itself

TTycho's PR has been open 16 months and the original author may have moved on. Two options:

- **Close #27 with a comment** linking to this proposal and the PR-A landing. Credit TTycho as the originator of the idea in PR-A's description.
- **Rebase #27 onto a working renderer** if TTycho is reachable and wants to land the original cyberthreat port on top. Same outcome with shared authorship.

Either way, this proposal is the route forward — #27 as it stands today is not mergeable without the renderer + migration story it sketches.
