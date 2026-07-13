# AI Analyst — Conversational Case Analysis in MatterBot

- **Date:** 2026-07-13
- **Status:** Design approved; ready for implementation planning
- **Related work:** #284 (indicator type routing — `commands/cmdutils.py`, `ACCEPTS`), #285 (no raw exceptions / secrets in channel)

## Summary

Add an optional AI "analyst" to MatterBot that a user talks to in natural language, in a Mattermost thread, to investigate a case together — and that uses MatterBot's existing command modules as tools to query threat-intel APIs on the user's behalf. The analyst reasons over the conversation, calls the relevant lookup modules, and synthesizes an analyst-voice narrative with the evidence.

The feature is **additive and optional**: with no `AI:` config it is inert and the existing bot is byte-for-byte unchanged.

## Goal & shape

An analyst types, in a channel:

> `@ai we're seeing beacons to 8.8.8[.]8 and a dropped file d41d…427e, thoughts?`

The bot replies in a thread: it auto-queries the two indicators the analyst named, synthesizes ("the hash is Emotet, the IP is clean — looks like staging"), and *proposes* a pivot ("want me to pull the linked C2 infra?"). The analyst replies "yes" in the thread; the bot continues. The thread is the case.

## Why MatterBot is well-suited

The command modules already form a tool registry, so the normally-hard part is done:
- **Tool name + description:** every module has `HELP['DEFAULT']['desc']` and `BINDS`.
- **Typed input contract:** `ACCEPTS` (from #284) gives each module a machine-readable indicator-type schema.
- **Uniform executor:** `call_module` → `process(command, channel, username, params, files, conn)` → `{'messages':[{'text':...}]}`.
- **Conversation threading:** `rootid` — a case is one thread.
- **Message ingress precedent:** `watch.scan_message` already runs on every message, proving a non-`@bind` hook point exists.
- **Per-user/channel ACLs:** `isallowed_module`.
- **Indicator classifier:** `cmdutils.classify()` (from #284) extracts and types indicators from text.

## Non-goals (v1)

- No write/destructive tools — read-only lookups only.
- No multi-argument tool calls — one `query` indicator per tool call (modules with optional extra params still work on the indicator alone).
- No text-protocol fallback for models that lack native function-calling — a function-calling-capable model is a documented requirement.
- No structured/summarized module return contract — the model consumes the modules' existing human-readable text output.
- No channel-wide context — context is strictly thread-scoped.

## Architecture

**A new isolated core module `ai_analyst.py`** holding an `AIAnalyst` class that owns the agent loop, the LLM client, tool-definition generation, and thread reconstruction. It is wired into `matterbot.py` dispatch: when the configured bind (`@ai`) is seen, dispatch calls `self.ai.handle(...)`.

`AIAnalyst` receives, by dependency injection:
- a **tool-executor callback** that wraps the existing module-execution path (reusing `call_module`, `isallowed_module`, timeouts) — so module execution and ACLs are reused, not reimplemented;
- an **LLM client** (thin `requests` wrapper — see Configuration);
- a **thread-fetch callback** and a **post callback** (Mattermost I/O), so the loop is testable with stubs.

Rationale for isolation (vs. inlining in `matterbot.py`): keeps `matterbot.py` dispatch thin; makes the LLM client and agent loop independently unit-testable with a stubbed executor and client; makes the feature removable (no AI config → `@ai` unregistered, nothing else changes).

## Interaction model

- Trigger: the configured bind `@ai` (default), reusing the existing bind + `rootid` threading machinery. Coexists with `@ioc` etc. in the same channels.
- An `@ai …` in a top-level channel message becomes the **root of a new thread** = a new case. Replies in that thread continue the same case.
- The AI reads **only that thread**, never other channel chatter.

## The agent loop (per turn)

1. **Reconstruct** the conversation from the thread (`rootid`) — see Conversation state.
2. **Build the tool set** — opt-in (`AITOOL`) modules, narrowed by `classify()` (see Tool exposure).
3. **Loop:** call the LLM with messages + tools. If it returns tool calls → execute them through the guarded executor, append results, call again. If it returns a text answer → post it and stop. Bounded by `max_iterations`.

## Autonomy guardrail (enforced in code, not the prompt)

The rule "auto-run tools on the indicators the analyst named; propose before pivoting to newly-discovered indicators" is a **hard invariant enforced at the executor**, not a prompt request — same fail-safe principle as #284.

Per-thread `authorized` indicator set:
- Every indicator `classify()` finds in a **user** message is added to `authorized`.
- The tool-executor **gates every call:** it classifies the tool's argument; if that indicator is not in `authorized`, it **refuses to run** and returns to the model: *"`<indicator>` hasn't been approved by the analyst — propose it, don't query it."* The model then surfaces the pivot in natural language and ends the turn.

So the model literally cannot execute a lookup on a newly-discovered indicator regardless of prompting; it can only ask.

**Pivot approval:** when the model proposes a pivot, the specific indicators it named are recorded as `pending` in derived thread state. On the analyst's next turn, an affirmative reply promotes `pending → authorized` (so the analyst says "yes" without re-typing the indicators). A clear "no" drops them. The affirmation reading is the model's job; the code backstop is that pivots are read-only lookups, so a misread is benign.

## Tool exposure

**Opt-in:** a module joins the AI toolbox with `AITOOL = True` in its `defaults.py` (loaded like `BINDS`/`ACCEPTS`, with `settings.py` override support). Curated: threat-intel lookups opt in; lolbin/free-text/paid-quota modules stay out unless an operator chooses.

**Tool definition, generated from existing metadata** (no new metadata to author):
```
name:        <module name>                e.g. "virustotal"
description: HELP['DEFAULT']['desc'] + " Accepts: " + ", ".join(ACCEPTS)
parameters:  { "type":"object",
               "properties": { "query": { "type":"string",
                                          "description":"the indicator to look up (<ACCEPTS types>)" } },
               "required": ["query"] }
```

**Execution mapping:** a tool call `virustotal(query="d41d…")` becomes `process(command=<module's first BIND>, channel, username, params=["d41d…"], files=[], conn)` run through the same executor as `@`-commands. Its returned message text is the tool result fed back to the model — and, in `full` mode, is also what is posted as inline evidence (model and analyst see identical bytes).

**Three code-level gates before any tool runs** (all reuse #284):
1. `authorized` set (autonomy guardrail);
2. `cmdutils.accepts()` — argument type must be in the module's `ACCEPTS`, else rejected back to the model;
3. `isallowed_module` — the AI cannot call a module the requesting user is barred from.

**Per-turn exposure:** modules whose `ACCEPTS` matches the indicator types *in this message* ∪ types *already authorized in the thread*. A purely conceptual turn with no indicators anywhere → no tools; the model converses from context.

## Conversation state — stateless, reconstructed from the thread

The bot keeps **no server-side session**; every piece of state is a pure function of the thread's posts, fetched by `rootid` each turn:
- **Message history:** user posts → `user` turns; the bot's own posts → `assistant` turns (identified by the bot's user id).
- **`authorized` set:** recomputed by `classify()` over the user posts.
- **Evidence mode:** the last `@ai brief`/`@ai full` toggle found in user posts, else the config default.
- **`pending` pivot:** indicators in the bot's most recent proposal, eligible for promotion if the current message approves.

Consequences:
- Survives restarts/redeploys with zero session loss (matches the module-reload/systemd resilience direction).
- Context is thread-scoped and isolated: two cases in one channel never bleed.

**Context bounding:** raw evidence tables (posted in `full` mode) are **marked when posted and excluded from reconstruction** — the model's memory of a past turn is the narrative it wrote, not the raw tables. A `max_history_turns` cap trims very long threads to the most recent N turns. Within a single turn, loop messages/results are ephemeral locals.

## Reply format

- **Default `compact`** (config default): analyst-voice narrative + a one-line `Queried: <module>(<arg>) → <verdict>` sources footer. No raw tables.
- **`full` (opt-in, sticky per thread):** narrative as the lead message, then the raw module outputs as follow-on messages (the same tables `@`-commands post), each **tagged as evidence** so reconstruction skips them.
- Analyst switches with `@ai full …` / `@ai brief …`; the choice sticks for that thread until changed.
- **Pivot proposal:** posted as the narrative; the turn ends awaiting yes/no.
- **Interim progress:** for slow multi-tool turns, an optional "Checking `8.8.8.8`, `d41d…`…" message so the thread isn't silent.
- **Tool failures never leak raw exceptions or key-bearing URLs into the channel** (reuses #285): a failed/timed-out tool returns a clean summary as the tool result; the model reports it in words; the channel never sees a traceback.

## Governance, safety & prompt injection

Everything funnels through the **single tool-executor choke point** — the only path from "model wants X" to "X happens" — which enforces, regardless of prompt:
- **ACLs** (`isallowed_module`);
- **type gate** (`cmdutils.accepts()`);
- **authorization** (`authorized` set);
- **caps** (`max_tool_calls_per_turn`, `max_tool_calls_per_thread`, `max_iterations`, per-call `timeout`) — bounding loop-runaway and paid-API spend.

**Prompt injection:** threat-intel results are attacker-influenceable (sample metadata, WHOIS/registrant fields, urlscan page text, MISP comments) and flow back as tool results, so indirect injection is in scope. Containment: the guardrail above is also the blast-radius limiter — even a hijacked model can only perform read-only, authorized, ACL-checked, rate-capped lookups. **No write/destructive tools exist in v1.** Tool results are injected as clearly-delimited *untrusted data*, and the system prompt instructs the model to treat them as evidence, not instructions. Worst realistic case: a wrong narrative, which a human is reading.

**Secrets:** the model never sees API keys (modules hold them internally); evidence posting reuses module output, which post-#285 carries no key-bearing URLs.

**Audit:** every tool call + argument is logged server-side regardless of evidence mode.

## Configuration

New top-level `AI:` section in `config.defaults.yaml` (parallel to `Matterbot:`/`Modules:`):

```yaml
AI:
  enabled: False            # master switch; off => @ai unregistered, zero impact
  base_url: "http://localhost:11434/v1"   # any OpenAI-compatible endpoint (Ollama shown)
  model: "<function-calling-capable model>"
  api_key: "<key, or 'ollama'>"
  bind: "@ai"               # the mention that triggers the analyst
  evidence: "compact"       # default reply mode; analyst uses `@ai full` per-thread
  max_tool_calls_per_turn: 8
  max_tool_calls_per_thread: 40
  max_iterations: 6         # LLM<->tool round-trips per turn
  timeout: 60               # seconds per LLM call
  max_history_turns: 20     # thread-reconstruction cap
  system_prompt: ""         # optional override of the built-in analyst prompt
```

**Operator requirements:**
- An OpenAI-compatible endpoint serving a **function-calling-capable** model (Ollama with a capable model, vLLM, LiteLLM, or a cloud API) — documented as a hard requirement in the README.
- At least one command module with `AITOOL = True`.

**Optional/inert:** no `AI:` block or `enabled: False` → the `@ai` bind is never registered; existing behavior unchanged.

**Dependency:** none new. The LLM client is a thin wrapper over `requests` (already a dependency) doing `POST {base_url}/chat/completions` with the `tools` parameter — matching the codebase's direct-`requests` style, avoiding the `openai` SDK.

## Testing strategy

`ai_analyst` is unit-tested with a **stubbed LLM client** (scripted tool-calls/answers) and a **stubbed tool-executor** — no network, stdlib-only, matching the `python -m unittest` CI runner. Coverage:
- tool-definition generation from a fake registry (`HELP`/`ACCEPTS` → schema);
- guardrail: un-authorized indicator blocked and surfaced as a proposal; authorized one runs; pivot proposal → approval promotion across turns;
- `ACCEPTS` + ACL rejections;
- caps enforced (max calls/turn, iteration cap ends the loop);
- evidence toggle (compact default; `full` sticky per thread);
- thread reconstruction: deriving `authorized`/mode/`pending` from a fake thread;
- tool error → clean summary, no raw exception (reuses #285).

The `requests`-based LLM client is a thin adapter; its HTTP is mocked/integration-tested separately. The loop logic is fully unit-testable by injecting the fake client. Existing `cmdutils` (classify/accepts) tests already cover the type layer.

## Files to add / change

- **New** `ai_analyst.py` — `AIAnalyst` class: LLM client (thin `requests` wrapper), tool-def generation, agent loop, guarded executor wrapper, thread reconstruction, reply formatting.
- **`matterbot.py`** — load `AITOOL` per module (alongside `BINDS`/`ACCEPTS`); register the `@ai` bind when `AI.enabled`; instantiate `AIAnalyst` with injected callbacks; dispatch `@ai` → `self.ai.handle(...)`.
- **`config.defaults.yaml`** — the `AI:` block above.
- **Per-module `defaults.py`** — add `AITOOL = True` to the curated starter set of threat-intel lookup modules (choose from the `@ioc`-bound, `ACCEPTS`-annotated set).
- **`tests/test_ai_analyst.py`** — the coverage above (stubbed client + executor).
- **README** — the AI section: config, the function-calling model requirement, opt-in `AITOOL`.

## Open questions / future extensions (explicitly out of v1)

- **Multi-argument tools** — expose optional module params (e.g. `abuseipdb maxAge`, `shodan --limit`) as additional tool parameters.
- **Text-protocol fallback** — a ReAct-style contract for models without native tool-calling.
- **Structured module return** — an LLM-friendly summarized return mode on modules (parallels the feeds-side `FeedResult` contract), to cut token cost vs. feeding human tables.
- **`cidr` and other indicator types** — the classifier vocabulary (including `cidr`, added in #284 follow-up) governs routing; new types extend reach.
- **Bind hygiene** — whether some `@ioc`-bound modules (actor-name, binary-name lookups) belong on shared binds at all is a separate product question.
