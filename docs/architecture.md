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

The main model could rewrite the prompt itself, but using a subagent pinned to Haiku keeps the rewriting step cheap regardless of what model the main session runs. If the user is on Opus, having Opus rewrite their prompt would cost ~20x more than Haiku for the same output quality on a mechanical restructuring task.

The split also keeps responsibilities clean: the main model does the context-aware extraction (it has the full conversation), and Haiku does the format-aware restructuring (it has a clear task and bounded input).

---

## V3 — Automatic Hook (Future)

The v3 design would add a `UserPromptSubmit` hook that intercepts every prompt before it reaches the main model and runs a lightweight classifier (also on Haiku) to decide: sanitize or pass through?

```
Every prompt → Hook → Haiku classifier (~100 tokens, ~$0.0001)
    ├── "clear enough" → proceed immediately
    └── "needs sanitizing" → invoke sanitizer → user confirms → Opus
```

The classifier prompt: "Is this prompt structured clearly enough for Opus to execute on the first attempt? Answer: CLEAR or SANITIZE."

Key constraint: the classifier must cost less than the expected saving from sanitizing. At Haiku prices, 100 tokens is ~$0.0001 — that's the break-even floor, easily cleared on any complex prompt.

Reference: [severity1/claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver) uses the same hook pattern for vague prompt detection.

---

## Contributing

The most valuable contributions:

1. **Better extraction heuristics** in `SKILL.md` — what instructions produce more accurate session context extraction, especially for vague prompts?
2. **Better rewriting rules** in `prompt-sanitizer.md` — what patterns consistently produce better Opus responses?
3. **More examples** in `examples/transformations.md` — real before/after from actual sessions, including cases where extraction was imperfect
4. **V3 hook implementation** — if you build it, open a PR with classifier accuracy benchmarks
