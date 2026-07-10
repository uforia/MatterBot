# Why command output needs Markdown sanitization

## The one-sentence reason

MatterBot renders **content it does not control** — third-party threat-intel feeds, external API responses, and CLI-tool output — directly into Mattermost Markdown, so anyone who controls that upstream content can inject Markdown that renders as *live formatting* in your channel.

MatterBot is a security bot. The content it displays is, by definition, attacker-adjacent: IOCs, phishing URLs, ransomware-leak text, scraped profiles, LLM output. Treating that text as trusted formatting is the bug.

## The trust boundary

```
   third-party feed / API / CLI tool          Mattermost channel
   (attacker can influence this) ──►  command.py  ──►  (renders Markdown live)
                                       ▲
                                  no escaping here
                                  = injection
```

Every `commands/*/command.py` builds a `{'text': ...}` string and hands it to Mattermost, which renders it as Markdown. If upstream text flows into that string without escaping, the upstream author — not MatterBot — decides how the channel message is formatted.

The `render_audit.py` detector (Part 2) found this is pervasive: **100 command modules, 0 escaping the structural Markdown vectors**, with **9** interpolating content straight into a code fence, **571** into inline-code, and **29** hand-rolling an incomplete `stripchars` filter.

## The four vectors, with real examples

Each helper exists because a specific Markdown construct can be *broken out of* by content placed inside it.

### 1. Code-fence breakout → `sanitize_block`

**Real site — `commands/chatgpt/command.py:49`:**
```python
reply = '\n```%s\n```' % (answer['choices'][0]['message']['content'][1:],)
```
The model's response is dropped inside a ` ``` ` fence. A fence is closed by the next line containing ` ``` `. So if the response *contains* ` ``` `, everything after it stops being code and renders as live Markdown.

**Attack.** The model (or a poisoned prompt, or a compromised API) returns:
```
here is your answer
```
# 🚨 SECURITY ALERT — click http://evil.example to re-auth
@channel
````
Rendered result: the fence closes early, then a forged `<h1>` heading and a real `@channel` ping fire in the SOC channel — a convincing phishing message wearing the bot's identity.

`sanitize_block` interposes a zero-width space between adjacent backticks, so no run in the content can close the fence. The visible backtick count is preserved, so legitimate code still looks right.

### 2. Inline-code breakout → `sanitize_inline`

**Real site — `commands/unfurl/command.py`** (URL echoed back in inline code):
```python
f"**Unfurl tree for `{url}`:**\n```\n{tree}\n```"
```
`url` comes from the user; `tree` from the unfurl tool. A backtick in either breaks the `` `…` `` wrap.

**Attack.** A URL like `` http://x`**@here click http://evil**` `` closes the inline code and injects a bold `@here` mention.

`sanitize_inline` strips backticks (and collapses newlines) so the wrapper can't be broken.

### 3. Blockquote injection → `sanitize_blockquote`

A leading `>` on a line starts a Mattermost blockquote. Feed content rendered at the start of a line (DM alerts, description fields) can forge quote structure to impersonate a "system" message. `sanitize_blockquote` escapes a leading `>` per line (`\>`), preserving indentation.

### 4. Heading / query-echo injection → `sanitize_heading_echo`

A leading `#` starts a heading. Modules that echo a user's query or a feed title at line start can be tricked into rendering an attacker's `# Big Official Heading`. `sanitize_heading_echo` collapses newlines to keep the echo one line and escapes a leading `#`/`>`.

## Why the existing `stripchars` idiom isn't enough

29 modules hand-roll this (from the module template):
```python
stripchars = r'\[\]\n\r\'\"|'
```
It removes brackets, quotes, pipes, and newlines — useful for table cells, but it **does not touch backticks, `>`, or `#`**, which are exactly the fence/blockquote/heading vectors above. So the modules that look like they're escaping are still open to the three highest-impact injections. Centralizing into `matterbot_formatting` replaces an incomplete, copy-pasted filter with one that covers the structural vectors and is unit-tested.

## Impact, concretely

Because this is a threat-intel bot, the injected content lands in the channel where analysts triage alerts. A feed/API/tool author (or anyone who can get a value into a feed MatterBot ingests) can:

- **Forge urgency and identity** — fake headings/blockquotes that look like official bot or system messages.
- **Fire `@channel` / `@here`** — noise, or social-engineering pressure ("click to re-auth now").
- **Plant phishing links** that render as clean, clickable Markdown inside a trusted security channel.
- **Corrupt formatting** so a real alert is buried or misread.

None of this requires code execution — it's pure output-integrity, and it's high-leverage precisely because the audience trusts the channel.

## What the three PRs do

1. **#251** adds the four `sanitize_*` helpers (dependency-free, `None`-safe) + tests.
2. **#252** adds `render_audit.py`, which finds every unsanitized site and (with `--check`) can gate the fence vector in CI.
3. **#253** converts the two clearest fence sites (`chatgpt`, `unfurl`); the detector's fence count drops 9 → 7 as objective proof. Remaining sites follow the same one-line pattern.
