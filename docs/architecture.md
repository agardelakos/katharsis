# Architecture

## Component Map

```
katharsis/
├── .claude-plugin/
│   └── marketplace.json          ← Plugin marketplace catalog
├── plugins/
│   └── katharsis/
│       ├── .claude-plugin/
│       │   └── plugin.json       ← Plugin manifest (name, description)
│       ├── agents/
│       │   └── prompt-sanitizer.md  ← Haiku-pinned subagent (the engine)
│       └── skills/
│           └── sanitize/
│               └── SKILL.md      ← What you invoke with /sanitize
├── examples/
│   └── transformations.md        ← Before/after examples
├── docs/
│   └── architecture.md           ← This file
└── README.md
```

---

## How the Components Relate

**The skill** (`SKILL.md`) is the orchestrator. It runs in the main session and is responsible for:
1. Extracting relevant context from the conversation history (automatic)
2. Reading any files pinned via `--` (explicit)
3. Invoking the subagent with both

**The subagent** (`prompt-sanitizer.md`) is the rewriter. It:
- Runs on Haiku (`model: haiku`) regardless of what model the main session uses
- Receives a structured input: raw prompt + session context + pinned files
- Applies rewriting rules and returns a single clean prompt

The skill handles the "what is relevant?" question. The subagent handles the "how should this be structured?" question. Neither tries to do both.

---

## Context Pipeline

Every `/sanitize` invocation runs two context layers before Haiku rewrites anything.

### Layer 1 — Automatic session context

The main session model scans the conversation history and extracts what is clearly relevant to the user's prompt. It targets under 150 tokens — a conservative distillation, not a full summary.

What it extracts:
- The core problem being worked on
- Approaches tried and why they failed
- Constraints or requirements that emerged during the session
- Specific files, functions, or error messages directly related to the prompt

**Extraction quality depends on prompt specificity.** A precise prompt ("fix the JWT refresh race condition") anchors the extraction clearly. A vague prompt ("fix the auth thing") gives weaker signal — the extractor may miss relevant context or pull in loosely related threads. The extractor is tuned to under-extract (leave things out) rather than over-extract (include noise), because false positives cost Opus tokens and can misdirect it.

This layer is most valuable in long sessions (20+ turns) with multiple failed attempts — exactly the case where you'd otherwise manually reconstruct context before sending to Opus.

### Layer 2 — Pinned file context (--)

Files referenced after `--` bypass relevance filtering and are always included. Use this when you know exactly what needs to be in the prompt.

```
/sanitize fix the race condition -- src/auth.dart logs/trace.log
```

Both layers combine: session context fills in what's already in the conversation; pinned files add what you're explicitly certain about.

---

## Token Flow

```
/sanitize fix the JWT race condition -- logs/auth.log

Main model (already loaded, ~free):
  ├── scans conversation history
  ├── produces session context block (~150 tokens)    ← ~$0.000002 (Sonnet output)
  └── reads logs/auth.log (pinned)

Haiku subagent receives:
  ├── raw prompt (~20 tokens)
  ├── session context (~150 tokens)
  └── distilled log content (variable)
  → rewrites → clean structured prompt (~300 tokens)
Cost: ~$0.001–0.003 total

User sends clean prompt to Opus:
  ├── no need to re-read conversation history
  ├── no clarifying questions about failed approaches
  └── executes on first attempt
Saving: typically $0.02–0.05 per avoided Opus clarification cycle
```

The 150-token context extraction overhead from the main model costs ~$0.000002. Avoiding a single Opus clarification turn (~1000 tokens in+out) saves ~$0.02. Break-even is essentially immediate.

---

## Why a Subagent for the Rewriting Step?

The main model could rewrite the prompt itself, but using a subagent pinned to Haiku keeps the rewriting step cheap regardless of what model the main session runs. If the user is on Opus, having Opus rewrite their prompt would cost ~5x more than Haiku for the same output quality on a mechanical restructuring task.

The split also keeps responsibilities clean: the main model does the context-aware extraction (it has the full conversation), and Haiku does the format-aware restructuring (it has a clear task and bounded input).

---

## V3 — Auto Mode Hook

Auto mode is opt-in. Users enable it per-project with `/sanitize_on` and disable it with `/sanitize_off`. When active, a `UserPromptSubmit` hook fires on every prompt and injects classifier instructions into the main model's context.

### Why a hook, and why opt-in

A `UserPromptSubmit` hook is the only mechanism that can intercept prompts before the main model sees them. Running it unconditionally on every prompt would add overhead to sessions where the user never needs sanitization — hence the flag file toggle. The hook is registered at the plugin level (always present) but becomes a no-op unless the flag file exists.

Slash commands are explicitly skipped. This means `/sanitize` still works as a one-off manual trigger regardless of whether auto mode is on or off.

### How the classifier works

The classifier is not a separate Haiku call. It is a set of instructions injected into the main model's context via `additionalContext`. The main model reads these instructions alongside the user's prompt and makes an inline decision:

```
Prompt arrives → hook fires → flag file exists?
    ├── No  → exit immediately, no output, no cost
    └── Yes → inject ~170-token additionalContext block
               ↓
               Main model reads: user prompt + classifier instructions
               ↓
               Inline assessment (a few tokens, no API call)
               ├── PASS THROUGH → respond directly, silently
               └── SANITIZE → extract context → Haiku rewrites → user confirms
```

This design was chosen deliberately over a separate Haiku classifier call. A separate call would cost ~$0.0001 and add latency on every prompt. The inline approach costs ~$0.000003 (170 injected tokens at Sonnet input pricing) and adds no latency because the main model is already reading the prompt anyway.

### Cost model for auto mode

| Event | Cost |
|---|---|
| Hook runs, flag absent | $0.00 |
| Hook runs, flag present, prompt passes through | ~$0.000003 |
| Hook runs, flag present, prompt gets sanitized | ~$0.001–0.003 |

The hook never calls the Anthropic API and requires no packages beyond the Python standard library. If Python is unavailable, it fails silently — auto mode degrades to a no-op, manual `/sanitize` is unaffected.

### Design trade-offs and honest limitations

**The real cost of auto mode is UX, not money.** Every complex prompt now pauses for a confirm step the user did not explicitly trigger. In a mixed session (short follow-ups interleaved with complex tasks), this can feel like interruption even though it is working as intended.

**The classifier accuracy depends on the main model's judgment.** It will occasionally assess a prompt as SANITIZE when the user considers it clear, or vice versa. There is no ground truth. The instructions are tuned to err toward SANITIZE in ambiguous cases (the cost of a false negative — skipping useful sanitization — is higher than the cost of a false positive — an unnecessary Haiku call).

**The hook cannot detect which model the user is targeting.** It fires on every non-slash-command prompt regardless of whether the user intends to work with Opus, Sonnet, or Haiku. Users targeting cheaper models during auto mode pay minor unnecessary overhead. This is a known limitation documented in the README.

### File layout for auto mode

```
plugins/katharsis/
├── hooks/
│   └── prompt-submit.py          ← UserPromptSubmit hook script
├── skills/
│   ├── sanitize_on/
│   │   └── SKILL.md              ← Creates .claude/katharsis_active
│   └── sanitize_off/
│       └── SKILL.md              ← Removes .claude/katharsis_active
```

The flag file (`.claude/katharsis_active`) lives in the user's project directory, not in the plugin. It should be added to `.gitignore` — it records local session preference, not project configuration.

---

## Contributing

The most valuable contributions:

1. **Better extraction heuristics** in `SKILL.md` — what instructions produce more accurate session context extraction, especially for vague prompts?
2. **Better rewriting rules** in `prompt-sanitizer.md` — what patterns consistently produce better Opus responses?
3. **Better classifier instructions** in `prompt-submit.py` — what `additionalContext` wording produces more accurate pass/sanitize decisions?
4. **More examples** in `examples/transformations.md` — real before/after from actual sessions, including cases where auto mode assessed correctly and incorrectly

---

## Future Work

### Adopt the Agent Plugins format?

[Agent Plugins](https://vercel.com/blog/introducing-agent-plugins) (launched August 2026) is an open, vendor-neutral packaging format for AI agent extensions — a root-level `plugin.json`, Skills under `skills/`, and MCP servers via `mcp.json`, with client-specific namespace directories for anything else. Launch adopters: ChatGPT, Cursor, GitHub Copilot, Kiro, VS Code.

**Not adopted as of 2026-08-09. Revisit if either changes:**

- **Claude Code isn't a launch adopter.** Katharsis targets Claude Code specifically; restructuring to a format the actual runtime doesn't consume buys nothing today.
- **The spec only standardizes Skills and MCP servers.** It has no defined place for a pinned subagent (`agents/prompt-sanitizer.md`, Katharsis's Haiku-pinning mechanism) or a `UserPromptSubmit` hook (`hooks/prompt-submit.py`, what drives auto mode). Both are load-bearing for this plugin's design — see "Why a Subagent for the Rewriting Step?" and "V3 — Auto Mode Hook" above — and neither maps onto the spec's two-component model.

If Claude Code later adopts Agent Plugins, or if it becomes worth offering a Skills-only subset of `/sanitize` (no auto mode, no Haiku-pinning) portable to Cursor/VS Code/etc., this is worth revisiting then.
