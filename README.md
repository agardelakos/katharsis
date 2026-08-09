# Katharsis

**Use a cheap model to prepare your prompts. Send only precision to the expensive one.**

Katharsis is a Claude Code skill + subagent that intercepts your messy, context-heavy prompts, rewrites them using Claude Haiku (fast, cheap), and hands you back a clean, structured prompt ready to fire at Claude Opus (powerful, expensive).

**This is a niche tool.** It is designed for complex, high-stakes prompts where you are deliberately reaching for Opus — the most capable and most expensive Claude model. It is not meant for everyday casual use. If you are chatting, asking quick questions, or working with Sonnet or Haiku already, this adds friction with no benefit.

The idea: Opus charges for every token it reads and writes. A poorly structured prompt wastes both. Haiku costs ~5x less per token than Opus — use it to do the cleanup work so Opus doesn't have to.

---

## How It Works

Katharsis has two modes. Both do the same thing — they differ only in who decides when to run.

**Manual mode** (default): you invoke `/sanitize` when you want it.

```
You type:  /sanitize fix the BLE handler that drops packets -- logs/ble_debug.log

Haiku:     reads the log → extracts relevant lines → restructures your prompt

You get:   a clean, precise prompt with distilled context embedded

You send:  that prompt to Opus → better result, fewer tokens, less back-and-forth
```

**Auto mode** (opt-in): you run `/sanitize_on` at the start of a session. From that point, every prompt is assessed automatically — complex ones are sanitized, simple ones pass through without interruption.

```
You type:  /sanitize_on         ← once, at session start

Later...

You type:  fix the race condition    ← no /sanitize needed
           ↓
           main model assesses: complex task with session history → sanitize
           ↓
Haiku:     extracts context → restructures prompt
           ↓
You get:   sanitized prompt + "Send to Opus, edit, or discard?"

You type:  run the tests        ← simple follow-up
           ↓
           main model assesses: clear, no benefit → passes through silently
```

You stay in control at every step. The sanitized prompt is always shown to you before anything is sent to Opus. You can send it as-is, edit it, or discard it.

---

## Why Bother?

| Without Katharsis | With Katharsis |
|---|---|
| Opus reads your full 500-line log | Opus reads 12 relevant lines |
| Vague prompt → Opus asks clarifying questions | Structured prompt → Opus executes first try |
| Failed attempt → you rewrite manually | Failed attempt → Haiku distills what went wrong |
| Every messy prompt costs Opus output tokens to untangle | Haiku untangles it for ~$0.001 |

**Token math example:**
- Haiku sanitization: ~500 tokens in + ~400 out = **~$0.0025**
- Opus reading 500 fewer input tokens: **~$0.0025 saved**
- Opus producing a more focused response (fewer output tokens): **~$0.005+ saved**
- Break-even on a single prompt. Any reduction in failed attempts is pure saving.

---

## When to Use It (and When Not To)

**Good fit:**
- You are about to send a complex prompt to Opus — multi-step, context-heavy, or with attached logs/files
- You just had a failed attempt and need to reframe what went wrong before trying again
- The task is ambiguous and you want to force-structure it before burning Opus output tokens on clarifying questions

**Not a good fit:**
- Everyday questions or casual conversation
- You are already using Sonnet or Haiku as your main model
- Your prompt is already clear and well-structured
- You need a quick answer and don't want to add a step

The rule of thumb: if you would not think twice before sending the prompt, don't bother. Katharsis is worth it when the cost of a failed or unfocused Opus response is higher than a few seconds of friction.

---

## Installation

### Option A — Plugin marketplace (recommended)

```bash
claude plugin marketplace add agardelakos/katharsis
claude plugin install katharsis@katharsis-marketplace
```

Restart Claude Code and verify with `/plugin` — `katharsis` should appear in the installed list.

### Option B — Global manual install (available in all projects)

`~/.claude` is Claude Code's global config directory — located at `C:\Users\<you>\.claude` on Windows or `~/.claude` on macOS/Linux. The `agents/` and `skills/` subdirectories do not exist by default; the commands below create them.

```bash
# Clone the repo
git clone https://github.com/agardelakos/katharsis.git
cd katharsis

# Copy subagent (the Haiku-pinned engine)
mkdir -p ~/.claude/agents
cp plugins/katharsis/agents/prompt-sanitizer.md ~/.claude/agents/prompt-sanitizer.md

# Copy skill (what you invoke)
mkdir -p ~/.claude/skills/sanitize
cp plugins/katharsis/skills/sanitize/SKILL.md ~/.claude/skills/sanitize/SKILL.md
```

### Option C — Project-level only

```bash
mkdir -p .claude/agents .claude/skills/sanitize
cp plugins/katharsis/agents/prompt-sanitizer.md .claude/agents/
cp plugins/katharsis/skills/sanitize/SKILL.md .claude/skills/sanitize/
```

---

## How context works

Every `/sanitize` invocation runs a two-layer context pipeline before Haiku touches your prompt.

**Layer 1 — Automatic session context**

The main model scans the conversation history and extracts what is clearly relevant to your prompt: the core problem, approaches that failed and why, constraints that emerged, specific files or functions mentioned. It distills this into a short block (~150 tokens) that gets passed to Haiku automatically — no `--` required.

This is the primary value-add for long sessions. After 30 turns and three failed attempts, Haiku knows what not to suggest. Opus never has to re-read the history or ask clarifying questions it could have answered from context.

**Extraction quality depends on prompt specificity.** A precise prompt ("fix the JWT refresh race condition on concurrent requests") gives the main model a clear anchor and produces accurate extraction. A vague prompt ("fix the auth thing") gives weaker signal — extraction may be incomplete or pull in loosely related threads. When in doubt, the extractor is tuned to under-extract rather than include noise.

**Layer 2 — Pinned file context (--)**

Files you reference after `--` bypass the relevance filter entirely and are always included. Use this when you know exactly what needs to be in the prompt and don't want to rely on automatic extraction.

```
/sanitize fix the packet drop issue -- logs/ble_debug.log
/sanitize fix the race condition -- src/auth.dart logs/trace.log
```

Both layers combine: automatic extraction covers the session history, `--` pins the files you're certain about.

---

## Auto mode

Auto mode is an opt-in feature for sessions where you want Katharsis to run without thinking about it. It is not the default and it is not for everyone. Read this section before enabling it.

### What it does

When auto mode is on, a hook fires on every prompt you send. The hook checks for a flag file in your project (`.claude/katharsis_active`). If the flag exists, it injects a short set of instructions into the main model's context. The main model then makes an inline assessment before responding:

| Prompt type | Decision | Your experience |
|---|---|---|
| Short follow-up ("run the tests", "apply that") | Pass through | No interruption — Katharsis is invisible |
| Simple question, clear instruction | Pass through | No interruption |
| Complex new task, vague with rich session history | Sanitize | Haiku rewrites → you confirm → proceed |
| Multi-step, references prior failures or constraints | Sanitize | Haiku rewrites → you confirm → proceed |

The assessment is **inline** — the main model decides as part of reading your prompt. There is no separate Haiku classifier call, no additional API round-trip, no external dependency.

### Honest cost breakdown

| Scenario | Cost |
|---|---|
| Auto mode OFF (flag file absent) | **$0.00** — hook exits after one file check |
| Auto mode ON, prompt passes through | **~$0.000003** — ~170 injected tokens at Sonnet input pricing |
| Auto mode ON, prompt gets sanitized | **~$0.001–0.003** — same as invoking `/sanitize` manually |

Auto mode does not cost more than manual on prompts that get sanitized. The extra cost is on prompts that pass through — roughly $0.000003 each, negligible in any realistic session.

**The real trade-off is UX, not money.** Complex prompts will pause for a confirm step you did not explicitly trigger. If your session is mostly quick iterative work, that pause will feel like friction. If your session is mostly complex standalone tasks, it will feel natural.

### When to enable it

**Good fit:**
- You are starting a dedicated session where you plan to send complex, multi-step prompts to Opus
- You want to stop thinking about when to invoke `/sanitize` and let the system decide
- Most of your prompts in this session will be new tasks, not short follow-ups

**Not a good fit:**
- Quick iterative work with lots of short follow-ups
- Sessions where you are using Sonnet or Haiku as your main model
- Any time the confirm step would feel like interruption rather than help
- If you are already disciplined about invoking `/sanitize` manually

### Enable and disable

```
/sanitize_on     enable auto mode for this project session
/sanitize_off    disable it
```

The flag is stored in `.claude/katharsis_active` inside your project directory. It is **project-scoped** — it only affects the project where you run `/sanitize_on`. It persists across Claude Code sessions until you explicitly remove it with `/sanitize_off`.

**This file should not be committed to git.** It records local session preference, not project configuration. Add it to your `.gitignore`:

```
.claude/katharsis_active
```

### What the hook does under the hood (transparency)

The hook is a Python script (`hooks/prompt-submit.py`) that runs on every prompt. Here is its complete logic:

1. Parse the JSON input from Claude Code
2. If the prompt starts with `/` (any slash command): exit immediately, do nothing
3. Check whether `.claude/katharsis_active` exists in the project directory
4. If the file does not exist: exit immediately, do nothing
5. If the file exists: output a JSON block with `additionalContext` — a ~170-token instruction block telling the main model to assess the prompt and run the sanitize pipeline if it would help

The hook never blocks a prompt, never calls the Anthropic API, and never requires any package beyond the Python standard library. If Python is not found in your PATH, the hook fails silently and auto mode degrades to a no-op — your prompts are unaffected.

## Usage

### Basic — session context is extracted automatically

```
/sanitize explain why my BLE GATT notification handler drops packets under high throughput
```

If you've been debugging this for 20 turns, Haiku already knows what you tried. No extra flags needed.

### Pin specific files with --

```
/sanitize fix the packet drop issue -- logs/ble_debug.log
```

```
/sanitize fix the crash -- logs/error.log logs/trace.log
```

### Both together — auto context + pinned files

```
/sanitize fix the queue implementation -- src/ble_handler.dart logs/deadlock_trace.log
```

Session history is extracted automatically; the files are pinned on top.

---

## What the output looks like

**Your prompt (after a long debugging session):**
```
fix the queue thing again
```

**What Haiku produces (with automatic session context):**
```
Goal: Fix packet drops in BLE GATT notification handler without breaking existing connection setup.

Session context:
- Previous fix: added CoroutineQueue at line 251 — caused deadlock when device disconnects mid-transfer
- Root cause identified: handler blocks main thread; queue didn't account for disconnect race condition
- Constraint from earlier: do not modify connectToDevice() or GATT service discovery

Steps:
1. Revise handleNotification() to use a non-blocking dispatch pattern that handles mid-transfer disconnects
2. Explicitly handle the disconnect-during-transfer race condition
3. Add a unit test for the disconnect edge case

Output: revised handleNotification() implementation + test, with inline comments on threading approach.
```

---

## Requirements

**For manual mode (`/sanitize`):**
- Claude Code (recent version with `model:` frontmatter support in subagents)
- A Claude subscription or API key with access to both Haiku and Opus

**For auto mode (`/sanitize_on`) — additionally:**
- Python 3 available in your PATH as `python3` or `python`
- No external packages required — only the Python standard library is used
- If Python is not found, the hook exits silently and auto mode becomes a no-op. Manual `/sanitize` is unaffected.

### Verify subagent model pinning works

```bash
claude --version
```

Check the [Claude Code changelog](https://code.claude.com/docs/en/changelog) to confirm your version supports `model:` in agent frontmatter. If not supported, the sanitizer still works — it just runs on your session's default model instead of Haiku.

---

## Roadmap

- **v1** — Manual invocation via `/sanitize`, explicit `--` file context
- **v2** — Automatic session context extraction from conversation history
- **v3** — Optional auto mode via `UserPromptSubmit` hook (`/sanitize_on` / `/sanitize_off`) — current

---

## Philosophy

This is a niche tool built for a specific workflow: complex sessions with Opus where prompt quality has real cost and quality consequences. It is not trying to be useful to everyone.

The hook pattern for v3 is inspired by [severity1/claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver) — worth studying if you want to understand progressive disclosure in Claude Code hooks.

---

## Compatible With

Follows the [open Agent Skills standard](https://agentskills.my/specification/). Works with Claude Code. The SKILL.md is portable — the subagent (model pinning) is Claude Code specific.

---

## License

MIT
