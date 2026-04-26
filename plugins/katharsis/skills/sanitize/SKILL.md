---
name: sanitize
description: Optimize a prompt for best results with Opus. Runs on Haiku (cheap) before sending to Opus (expensive). Use when your prompt is complex, messy, context-heavy, or after a failed attempt. Not for everyday casual use — only worth it when you are deliberately reaching for Opus on a hard task.
agent: prompt-sanitizer
---

Sanitize the following prompt using the prompt-sanitizer agent:
$ARGUMENTS

## Step 1 — Extract session context (automatic)

Review the conversation history above and extract context that is clearly relevant to the user's prompt. Be conservative: when in doubt, leave it out. A false positive (irrelevant context included) is worse than a false negative, because noise in the final prompt costs Opus tokens and can misdirect it.

Extract only:
- The core problem being worked on, if established
- Approaches that have been tried and why they failed
- Constraints or requirements that emerged during the session
- Specific file paths, function names, or error messages directly related to the prompt

Summarise in a brief "Session context" block, targeting under 150 tokens. If the conversation contains no clearly relevant prior context, write: "No prior session context."

Note: extraction quality depends on how specific the user's prompt is. A precise prompt ("fix the JWT refresh race condition") anchors the search clearly. A vague prompt ("fix the auth thing") gives weaker signal — prefer to under-extract rather than pull in loosely related threads.

## Step 2 — Handle pinned file context (--)

Parse the user's raw prompt from $ARGUMENTS. If files are referenced after `--`, read each one using the Read tool. These are pinned — they bypass the relevance filter and are always included regardless of what Step 1 found.

Examples:
/sanitize fix the crash -- logs/error.log
/sanitize fix the race condition -- src/auth.dart logs/trace.log

If no `--` files are present, skip this step.

## Step 3 — Invoke the subagent

Pass to the prompt-sanitizer agent:
- Raw prompt: the user's input from $ARGUMENTS (everything before --)
- Session context: the block produced in Step 1
- Pinned files: contents of any -- files from Step 2 (if any)

## Step 4 — Present the result

After the sanitizer returns, present the optimised prompt to the user clearly, then ask:

"Send this to Opus, edit it first, or discard?"

Wait for the user's choice before proceeding.
