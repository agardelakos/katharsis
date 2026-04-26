# Katharsis

**Use a cheap model to prepare your prompts. Send only precision to the expensive one.**

Katharsis is a Claude Code skill + subagent that intercepts your messy, context-heavy prompts, rewrites them using Claude Haiku (fast, cheap), and hands you back a clean, structured prompt ready to fire at Claude Opus (powerful, expensive).

**This is a niche tool.** It is designed for complex, high-stakes prompts where you are deliberately reaching for Opus — the most capable and most expensive Claude model. It is not meant for everyday casual use. If you are chatting, asking quick questions, or working with Sonnet or Haiku already, this adds friction with no benefit.

The idea: Opus charges for every token it reads and writes. A poorly structured prompt wastes both. Haiku costs ~20x less — use it to do the cleanup work so Opus doesn't have to.

---

## How It Works

```
You type:  /sanitize fix the BLE handler that drops packets -- logs/ble_debug.log

Haiku:     reads the log → extracts relevant lines → restructures your prompt

You get:   a clean, precise prompt with distilled context embedded

You send:  that prompt to Opus → better result, fewer tokens, less back-and-forth
```

You stay in control at every step. The sanitized prompt is shown to you before anything is sent to Opus. You can send it as-is, edit it, or discard it.

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

### Option A — Global (available in all projects)

`~/.claude` is Claude Code's global config directory — located at `C:\Users\<you>\.claude` on Windows or `~/.claude` on macOS/Linux. The `agents/` and `skills/` subdirectories do not exist by default; the commands below create them.

```bash
# Clone the repo
git clone https://github.com/agardelakos/katharsis.git
cd katharsis

# Copy subagent (the Haiku-pinned engine)
mkdir -p ~/.claude/agents
cp .claude/agents/prompt-sanitizer.md ~/.claude/agents/prompt-sanitizer.md

# Copy skill (what you invoke)
mkdir -p ~/.claude/skills/sanitize
cp .claude/skills/sanitize/SKILL.md ~/.claude/skills/sanitize/SKILL.md
```

### Option B — Project-level only

```bash
mkdir -p .claude/agents .claude/skills/sanitize
cp .claude/agents/prompt-sanitizer.md .claude/agents/
cp .claude/skills/sanitize/SKILL.md .claude/skills/sanitize/
```

---

## Usage

### Basic — just restructure your prompt

```
/sanitize explain why my BLE GATT notification handler drops packets under high throughput
```

### With context files — Haiku reads and distills them for you

```
/sanitize fix the packet drop issue -- logs/ble_debug.log
```

```
/sanitize fix the crash after 3 failed attempts -- logs/error.log logs/trace.log
```

### With previous failed attempt context

```
/sanitize fix the queue implementation, previous attempt added a coroutine but it deadlocked -- src/ble_handler.dart logs/deadlock_trace.log
```

---

## What Haiku Does to Your Prompt

**Before:**
```
fix the bug in the BLE thing, it keeps dropping, i tried adding a queue but it broke,
check the logs maybe, also dont break the other stuff
```

**After:**
```
Goal: Fix packet drops in BLE GATT notification handler without breaking existing connection setup.

Context (from logs/ble_debug.log):
- Drop occurs at handleNotification() line 247 under >10 concurrent notifications
- Previous fix: added CoroutineQueue at line 251 — caused deadlock when device disconnects mid-transfer (log line 891)
- Root cause: handler blocks main thread; queue didn't account for disconnect race condition

Steps:
1. Revise handleNotification() to use a non-blocking dispatch pattern that handles mid-transfer disconnects
2. Do NOT modify connectToDevice() or the GATT service discovery logic
3. Add a unit test for the disconnect-during-transfer edge case

Output: revised handleNotification() implementation + test, with inline comments explaining the threading approach.
```

---

## Requirements

- Claude Code (recent version with `model:` frontmatter support in subagents)
- A Claude subscription or API key with access to both Haiku and Opus

### Verify subagent model pinning works

```bash
claude --version
```

Check the [Claude Code changelog](https://code.claude.com/docs/en/changelog) to confirm your version supports `model:` in agent frontmatter. If not supported, the sanitizer still works — it just runs on your session's default model instead of Haiku.

---

## Roadmap

- **v1.0** — Manual invocation via `/sanitize` (current)
- **v2.0** — Optional `UserPromptSubmit` hook that auto-evaluates every prompt and sanitizes only when beneficial (no-op for clear prompts)

---

## Philosophy

This is a niche tool built for a specific workflow: complex sessions with Opus where prompt quality has real cost and quality consequences. It is not trying to be useful to everyone.

The hook pattern for v2 is inspired by [severity1/claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver) — worth studying if you want to understand progressive disclosure in Claude Code hooks.

---

## Compatible With

Follows the [open Agent Skills standard](https://agentskills.my/specification/). Works with Claude Code. The SKILL.md is portable — the subagent (model pinning) is Claude Code specific.

---

## License

MIT
