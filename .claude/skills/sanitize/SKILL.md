---
name: sanitize
description: Optimize a prompt for best results with Opus. Runs on Haiku (cheap) before sending to Opus (expensive). Use when your prompt is complex, messy, context-heavy, or after a failed attempt. Not for everyday casual use — only worth it when you are deliberately reaching for Opus on a hard task.
agent: prompt-sanitizer
---

Sanitize the following prompt using the prompt-sanitizer agent:
$ARGUMENTS

Instructions for the sanitizer agent

Parse the user's raw prompt from $ARGUMENTS
Check if any context sources were referenced (log files, error outputs, previous attempts) using -- as separator. Examples:

/sanitize fix the BLE handler -- logs/ble_debug.log
/sanitize fix the crash -- logs/error.log logs/trace.log

If context files are referenced, use the Read tool to open them, then distill only the causally relevant content
Rewrite the prompt following your rewriting rules
Return ONLY the final optimized prompt — nothing else

After the sanitizer returns
Present the optimized prompt to the user clearly, then ask:

"Send this to Opus, edit it first, or discard?"

Wait for the user's choice before proceeding.
