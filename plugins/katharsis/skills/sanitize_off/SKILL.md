---
name: sanitize_off
description: Disable Katharsis auto-sanitize mode for this project. Prompts will no longer be assessed automatically. You can still use /sanitize at any time for one-off manual sanitization.
---

Disable Katharsis auto-sanitize mode by removing the flag file.

Run this bash command to remove it:

```bash
rm -f .claude/katharsis_active
```

Then confirm to the user with this exact message:

---

**Katharsis auto-sanitize mode is now OFF** for this project.

The hook will still fire on every prompt (it is registered at the plugin level), but it now exits immediately after finding no flag file — zero cost, zero effect.

You can still use `/sanitize <prompt>` at any time for one-off manual sanitization. Nothing else has changed.

To re-enable auto mode: `/sanitize_on`

---
