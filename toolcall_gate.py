#!/usr/bin/env python3
"""Does the model emit tool calls in the shape LLMClient expects?

Run from the MatterBot repo root against the same endpoint and model the bot's
AI: config block uses. Touches no Mattermost and no command modules; it sends
one bare request (one user message, one tool schema, no system prompt) through
the real LLMClient and checks the structured `tool_calls` that come back.

  AI_BASE_URL=https://llm.example/v1 AI_API_KEY=... \
      python3 toolcall_gate.py <model-id> [<model-id> ...]

Exit 0 = every model tool-called on every attempt. Exit 1 = at least one did not.

Scope: first round only. It does not replay a tool result back to the model, so
it cannot show whether the bot's later rounds (system prompt, wrapped tool
results) are what make a model stop tool-calling natively.
"""
import os
import sys

# Python puts the SCRIPT's directory on sys.path, not the cwd — so this works
# when the gate lives outside the repo but is run from the repo root.
sys.path.insert(0, os.getcwd())

from ai_analyst import LLMClient, build_tool_definitions  # noqa: E402

ATTEMPTS = int(os.environ.get('AI_GATE_ATTEMPTS', '5'))

# A stand-in for one entry of the real registry. Shaped exactly as
# AIAnalyst._registry() produces, so the tool schema is the real one.
REGISTRY = {
    'crtsh': {
        'binds': ['@crtsh'],
        'accepts': ['domain'],
        'help': {'DEFAULT': {'desc': 'Query crt.sh for certificates.'}},
        'aitool': True,
    },
}
PROMPT = 'Look up the certificates for evil.example.com.'


def probe(client, tools):
    """One round-trip. Returns (ok, detail)."""
    try:
        reply = client.chat([{'role': 'user', 'content': PROMPT}], tools)
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'

    calls = reply['tool_calls']
    if not calls:
        # Distinguish "the model can't tool-call" from "the server didn't parse
        # the call it made". The server parses tool calls in the dialect the
        # model's chat template defines; a call written in any other dialect is
        # handed back as plain text in `content` or `reasoning`. Same symptom,
        # different fix -- so look in both, and show what was actually emitted.
        for field in ('content', 'reasoning'):
            text = reply.get(field) or ''
            leaked = [m for m in ('crtsh', 'tool_call', 'function', 'invoke', '<|',
                                  'evil.example.com') if m in text]
            if leaked:
                return False, (f'no tool_calls, but {field} leaks {leaked} — the call '
                               f'was made but not parsed: {text[:300]!r}')
        return False, f'no tool_calls; content={reply["content"][:120]!r}'

    call = calls[0]
    if call['name'] != 'crtsh':
        return False, f'wrong tool: {call["name"]!r}'
    query = call['arguments'].get('query')
    if not query:
        # _normalise_tool_calls swallowed unparseable arguments — the executor
        # would reject this cleanly, but it means the model emitted junk JSON.
        return False, f'empty/unparseable arguments: {call["arguments"]!r}'
    if 'evil.example.com' not in str(query):
        return False, f'wrong query: {query!r}'
    return True, f'query={query!r}'


def main():
    base_url = os.environ.get('AI_BASE_URL')
    api_key = os.environ.get('AI_API_KEY')
    models = sys.argv[1:]
    if not base_url or not api_key or not models:
        sys.exit('need AI_BASE_URL, AI_API_KEY and at least one model argument')

    tools = build_tool_definitions(REGISTRY, {'domain'})
    if not tools:
        sys.exit('build_tool_definitions returned no tools — registry shape is wrong')
    print(f'tool schema offered to the model:\n  {tools[0]}\n')

    all_passed = True
    for model in models:
        client = LLMClient(base_url=base_url, api_key=api_key, model=model,
                           timeout=int(os.environ.get('AI_TIMEOUT', '60')))
        passes = 0
        print(f'--- {model} ---')
        for i in range(1, ATTEMPTS + 1):
            ok, detail = probe(client, tools)
            passes += ok
            print(f'  attempt {i}: {"PASS" if ok else "FAIL"}  {detail}')
        rate = passes / ATTEMPTS
        print(f'  => {passes}/{ATTEMPTS} ({rate:.0%})')
        # Temperature is 0 in the real client. Anything short of unanimous means
        # the model is non-deterministic on the one behaviour the design needs.
        if passes != ATTEMPTS:
            all_passed = False
            print('  VERDICT: not usable as-is — the analyst needs this every turn,'
                  ' not most turns.\n')
        else:
            print('  VERDICT: usable.\n')

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
