#!/usr/bin/env python3
"""
Katharsis UserPromptSubmit hook.

Fires on every user prompt. Does one thing: checks whether auto-sanitize mode
is active for the current project. If it is, injects instructions for the main
model to assess the prompt and run the sanitize pipeline when it would help.

What this script does NOT do:
- Call the Anthropic API
- Require any external packages (standard library only)
- Block any prompts
- Run on slash commands

Cost when auto mode is OFF:  zero — the file check exits immediately.
Cost when auto mode is ON:   ~170 tokens of additionalContext injected per prompt
                              (~$0.0000025 at Sonnet input pricing).
                              The classifier assessment itself costs a few more tokens
                              inline, but no separate agent or API call is made.

Flag file: .claude/katharsis_active in the project working directory (cwd).
Created by /sanitize_on, removed by /sanitize_off.
"""

import json
import os
import sys

# Instructions injected into the main model's context when auto mode is active.
# The main model reads this alongside the user's prompt and decides whether to
# sanitize before responding. No separate Haiku call is made for classification —
# the main model does the assessment inline.
ADDITIONAL_CONTEXT = """[KATHARSIS AUTO-SANITIZE MODE IS ACTIVE]

Before processing the user's prompt, make a quick inline assessment — no separate agent call needed:

PROCEED DIRECTLY (no interruption, no mention of Katharsis) if the prompt is:
- A short follow-up or continuation ("apply that", "run the tests", "explain the last change")
- Conversational or a simple factual question
- Already specific and well-structured with no clear benefit from rewriting

RUN THE FULL SANITIZE PIPELINE if the prompt is:
- A new, complex, or multi-step task
- Vague, but there is relevant session history that would meaningfully enrich it
- Something where Opus receiving a structured prompt would likely save clarification turns or failed attempts

If you run the sanitize pipeline:
1. Extract relevant session context from conversation history (conservative, ~150 tokens)
2. Invoke the prompt-sanitizer agent with the raw prompt + session context
3. Present the sanitized result clearly
4. Ask: "Send this to Opus, edit it first, or discard?"
5. Wait for the user's choice before proceeding with the original task

If you proceed directly, do so silently — no mention of this assessment or of Katharsis."""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        # Malformed input — proceed normally, never block
        sys.exit(0)

    prompt = data.get("prompt", "").strip()
    cwd = data.get("cwd", "")

    # Skip all slash commands — /sanitize, /sanitize_on, /sanitize_off, everything
    if prompt.startswith("/"):
        sys.exit(0)

    # Check for the project-level flag file
    if not cwd:
        sys.exit(0)

    flag_path = os.path.join(cwd, ".claude", "katharsis_active")
    if not os.path.exists(flag_path):
        sys.exit(0)

    # Auto-sanitize mode is active — inject the classifier instructions
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ADDITIONAL_CONTEXT
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
