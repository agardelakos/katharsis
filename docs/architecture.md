# Architecture

## Component Map

```
katharsis/
├── .claude-plugin/
│   └── marketplace.json          ← Plugin marketplace catalog
├── plugins/
│   └── katharsis/
│       ├── .claude-plugin/
│       │   └── plugin.json       ← Plugin manifest (version, name)
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

## How the Two Files Relate

**The skill** (`SKILL.md`) is the interface. It defines:
- The `/sanitize` slash command
- How to parse `$ARGUMENTS` (prompt + optional context files after `--`)
- The post-sanitization UX (show output, ask user what to do next)

**The subagent** (`prompt-sanitizer.md`) is the engine. It defines:
- `model: haiku` — pins Claude Haiku regardless of what model the main session uses
- `tools: Read, Glob, Grep` — lets it read context files you reference
- The rewriting rules Haiku follows

The skill delegates to the subagent via `agent: prompt-sanitizer` in its frontmatter. Claude Code handles the handoff.

---

## Why a Subagent and Not Just a Skill?

A plain skill runs in the main session context — same model, same conversation history, output goes directly into the thread. That works for many things, but for our use case we need model pinning.

The subagent runs in an isolated context with a pinned model (`haiku`). It receives the task, does its work, returns a result to the main session. The main session (Opus or Sonnet) then presents the result to you.

This is also why the subagent instructions say "return ONLY the rewritten prompt" — we don't want its reasoning cluttering the main session context that Opus will later read.

---

## Token Flow

```
Your prompt (~50-300 tokens)
    ↓
Skill parses arguments — negligible
    ↓
Subagent (Haiku) receives:
  - Subagent system prompt (~200 tokens)
  - Your raw prompt (~50-300 tokens)
  - Context files if referenced (variable, but Haiku reads them cheaply)
    ↓
Haiku output: optimized prompt (~200-500 tokens)
Cost: ~$0.001–0.003
    ↓
Main session presents result to you
    ↓
You send optimized prompt to Opus
  - Cleaner input = fewer output tokens from Opus
  - Less back-and-forth = fewer total turns
Net saving: typically $0.005–0.02 per sanitized prompt on complex tasks
```

---

## V2 — Automatic Hook (Future)

The v2 design would add a `UserPromptSubmit` hook that intercepts every prompt and runs a lightweight classifier (also on Haiku) to decide: sanitize or pass through?

```
Every prompt → Hook → Haiku classifier (~100 tokens)
    ├── "clear enough" → proceed immediately (100 token overhead, that's all)
    └── "needs sanitizing" → invoke sanitizer → show result → user confirms → Opus
```

The classifier prompt would be something like:
> "Is this prompt structured clearly enough for Opus to execute on the first attempt, or would it benefit from restructuring? Answer: CLEAR or SANITIZE."

Key design constraint: the classifier must cost less than the expected saving from sanitizing. At Haiku prices, 100 tokens is ~$0.0001. That's the break-even floor.

Reference: [severity1/claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver) uses the same hook pattern for vague prompt detection — study that before building v2.

---

## Contributing

The most valuable contributions right now:

1. **Better rewriting rules** in `prompt-sanitizer.md` — what patterns consistently produce better Opus responses?
2. **More examples** in `examples/transformations.md` — real before/after from actual sessions
3. **Domain-specific variants** — e.g. a sanitizer tuned for IoT/embedded prompts, or Flutter/Dart prompts
4. **V2 hook implementation** — if you build it, open a PR with benchmark data showing the classifier accuracy
