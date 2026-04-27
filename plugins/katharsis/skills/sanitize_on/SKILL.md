---
name: sanitize_on
description: Enable Katharsis auto-sanitize mode for this project. When active, every prompt is assessed automatically — complex prompts are sanitized by Haiku before you send them to Opus, simple prompts pass through without interruption.
---

Enable Katharsis auto-sanitize mode for this project by creating the flag file.

Run this bash command to create it:

```bash
mkdir -p .claude && touch .claude/katharsis_active
```

Then confirm to the user with this exact message, formatted clearly:

---

**Katharsis auto-sanitize mode is now ON** for this project.

**What just changed:** a lightweight hook will now fire on every prompt you send. The hook itself only checks whether this flag file exists — it costs nothing and adds no latency. When it finds the flag, it asks the main model to assess your prompt before responding.

**How the assessment works:**

The main model makes a quick inline decision — no separate API call, no extra Haiku invocation:

| Your prompt | What happens | Your experience |
|---|---|---|
| Short follow-up, simple question, clear instruction | Passes through directly | No interruption — Katharsis is invisible |
| Complex task, vague with rich session history, multi-step | Full sanitize pipeline runs | Haiku rewrites → you confirm → Opus gets a clean prompt |

**What this costs:**

- Prompts that pass through: ~$0.000003 (a few classifier tokens — effectively zero)
- Prompts that get sanitized: ~$0.001–0.003 (same as invoking `/sanitize` manually)
- Auto mode being OFF: exactly $0.00

Auto mode does not cost more than manual on prompts that get sanitized. The only extra cost is the classifier assessment on prompts that don't — negligible.

**The honest trade-off:** complex prompts will pause for a confirm step that you didn't explicitly trigger. This is intentional — you stay in control of what goes to Opus. But it does add a moment of friction to the workflow. If that friction feels wrong in your current session, use `/sanitize_off` to return to manual mode.

**When this is a good fit:**
- You are starting a dedicated Opus session where most prompts will be complex and standalone
- You want to stop thinking about when to invoke `/sanitize` — let the system decide

**When this is not a good fit:**
- Quick iterative work with lots of short follow-ups ("run the tests", "apply that")
- Sessions where you are using Sonnet or Haiku as your main model
- Any time the extra confirm step would feel like interruption rather than help

**To disable:** type `/sanitize_off` at any time.

**Flag file location:** `.claude/katharsis_active` in this project directory. The flag persists across Claude Code sessions until you explicitly remove it with `/sanitize_off`.

**Git note:** this file records local session preference and should not be committed. If this is a git project, consider adding it to `.gitignore`:
```
.claude/katharsis_active
```

---
