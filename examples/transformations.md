# Katharsis — Real Examples

These show actual before/after transformations across common Claude Code scenarios.

---

## Example 1 — Vague bug fix

**Command:**
```
/sanitize fix the BLE thing
```

**Before (your prompt):**
```
fix the BLE thing
```

**After (Haiku output):**
```
Goal: Diagnose and fix the BLE GATT notification handler issue in this project.

Steps:
1. Identify the specific failure mode (drops, timeouts, connection loss, or notification queue overflow)
2. Locate the relevant handler code
3. Implement a fix that addresses the root cause
4. Do not modify unrelated BLE connection or pairing logic

Output: fixed code with a brief comment explaining what was wrong and why the fix works.
```

---

## Example 2 — Context-heavy with log file

**Command:**
```
/sanitize fix the packet drop -- logs/ble_debug.log
```

**Before (your prompt):**
```
fix the packet drop -- logs/ble_debug.log
```

**After (Haiku reads log, extracts relevant lines, rewrites):**
```
Goal: Fix BLE GATT notification packet drops occurring under high throughput in handleNotification().

Context (distilled from logs/ble_debug.log):
- Drops begin at >10 concurrent notifications (log line 247)
- Handler blocks main thread for ~340ms per notification under load (line 312)
- No drops observed below 5 concurrent notifications
- Previous coroutine queue attempt caused deadlock on device disconnect (line 891)

Steps:
1. Refactor handleNotification() to process notifications off the main thread
2. Handle the disconnect-during-processing race condition explicitly
3. Do NOT change the GATT service discovery or connection setup code

Constraints:
- Must remain compatible with Android API 26+
- Do not introduce new dependencies

Output: revised handleNotification() with inline comments on threading approach.
```

---

## Example 3 — After a failed attempt

**Command:**
```
/sanitize the coroutine fix didn't work, it deadlocked -- src/ble_handler.dart logs/deadlock.log
```

**After:**
```
Goal: Fix deadlock introduced by coroutine queue in handleNotification() in src/ble_handler.dart.

Context (from logs/deadlock.log and src/ble_handler.dart):
- Deadlock occurs when device disconnects while a notification is mid-processing (line 891 in log)
- Current implementation acquires mutex at line 251, but disconnect callback also tries to acquire it (line 178)
- The coroutine queue itself is correctly structured — the issue is mutex contention on disconnect

Previous failed approach: Added CoroutineQueue — correct idea but mutex not released on disconnect path.

Steps:
1. Ensure the disconnect callback releases or avoids the mutex before the queue clears
2. Consider a tryLock pattern or restructuring the disconnect path to not require the lock
3. Add a test case: connect → start notification transfer → disconnect → verify no deadlock

Output: revised ble_handler.dart with the deadlock fix, plus the test case.
```

---

## Example 4 — Multi-step feature request

**Command:**
```
/sanitize add dark mode to the settings screen and make sure it persists
```

**After:**
```
Goal: Add persistent dark mode toggle to the settings screen.

Steps:
1. Add a dark mode toggle UI element to the settings screen
2. Implement theme switching logic (light/dark) that applies app-wide
3. Persist the user's preference across app restarts using SharedPreferences (or the existing persistence layer if one exists)
4. Apply the saved preference on app launch before the first frame renders to avoid flash

Constraints:
- Follow existing settings screen UI patterns
- Do not change any screen other than settings and the app-level theme wrapper

Output: all modified/created files with no placeholder TODOs.
```

---

## Example 5 — Refactoring with constraints

**Command:**
```
/sanitize refactor the auth module its a mess but dont break the existing API
```

**After:**
```
Goal: Refactor the auth module internals for clarity and maintainability without changing its public API.

Steps:
1. Identify the public API surface (exported functions, classes, types) — these must remain unchanged
2. Reorganize internal structure: split large functions, clarify naming, remove duplication
3. Add inline comments where the logic is non-obvious
4. Verify all existing call sites still compile without changes

Constraints:
- Public API signatures must not change
- Do not add new dependencies
- Do not change authentication logic — only structure and readability

Output: refactored module files. If any public API change is unavoidable, flag it explicitly before making it.
```
