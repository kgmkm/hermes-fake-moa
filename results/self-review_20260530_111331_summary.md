# Fake MoA Results — `self-review`

**Time**: 20260530_111331  
**Models**: 4  
**Prompt** (2268 chars):
> You are a senior code reviewer. Review the following 4 Python scripts from the "hermes-fake-moa" project (a Hermes Agent skill for parallel multi-LLM orchestration).

**Your task**: Read ALL of the following files using the `read_file` tool, then provide a thorough review.

Files to read:
1. /mnt/y/...

## Status

| # | Model | Provider | Status | Time |
|---|-------|----------|--------|------|
| 1 | `kimi-k2.6` | opencode-go | ❌ | 22.7s |
| 2 | `glm-5.1` | opencode-go | ✅ | 68.0s |
| 3 | `mimo-v2.5-pro` | opencode-go | ✅ | 87.7s |
| 4 | `minimax-m2.7` | opencode-go | ❌ | 25.4s |

## Comparison

| Model | Preview |
|-------|--------|
| `glm-5.1` | All four files loaded. Let me now provide a thorough review.  ---  ## Code Review: hermes-fake-moa v1.3.0  ### A. Script... |
| `mimo-v2.5-pro` | Here is the full code review.  =======================================================================                  ... |

## Responses

### ❌ kimi-k2.6 (`opencode-go` — 22.7s)

```

```
**Error**: `Loading weights:   0%|          | 0/152 [00:00<?, ?it/s]
Loading weights:  51%|█████     | 77/152 [00:00<00:00, 768.05it/s]
Loading weights: 100%|██████████| 152/152 [00:00<00:00, 865.75it/s]

Batches`

---

### ✅ glm-5.1 (`opencode-go` — 68.0s)

All four files loaded. Let me now provide a thorough review.

---

## Code Review: hermes-fake-moa v1.3.0

### A. Script Logic & Potential Bugs

- **CRITICAL — `run_model` temp-file cleanup race condition on exception path**: The `finally` block at line 174-180 cleans up `tmpfile`, but `tmpfile` is only assigned inside the `if len(prompt) > ARG_MAX_THRESHOLD:` branch (line 81). If an exception occurs before that branch executes (e.g., in the `cmd` list construction), `tmpfile` is still `None` and the `finally` passes harmlessly. However, the real issue is that `tmpfile` is **defined at line 79 as `None`** and reassigned at line 81 conditionally. If the `NamedTemporaryFile` write itself (line 85) raises, the file was created with `delete=False` but `tmpfile.name` may not be captured for cleanup. Actually, it IS captured because the assignment happens before `.write()`. The cleanup is correct — **this is fine**, just noting it's a subtle pattern.

- **WARNING — `time.sleep()` inside `threading.Lock` in `submit_with_delay`**: Lines 201-207 hold `submit_lock` while calling `time.sleep(wait)`. This means all threads block on the lock while one thread sleeps. Since the lock is held during the sleep, the second thread waiting for the lock will acquire it, compute a potentially zero wait (because the elapsed time since last submit already exceeded `delay`), and proceed immediately. The **intended staggered behavior** is actually achieved (the lock serializes submissions), but this is inefficient — threads are blocked on the lock doing nothing while one sleeps. A better pattern would record the planned start time under the lock, release the lock, then sleep until that planned time. The current implementation works but wastes thread readiness.

- **WARNING — `_fmt()` function duplicated**: `_fmt()` is defined in both `list-models.py` (line 419) and `select-panel.py` (line 115). These are slightly different implementations: list-models outputs `$X.XX` format, select-panel outputs `$X.XX/M`. If one changes, the other won't. Should be extracted to a shared utility module.

- **WARNING — `load_all_models` suppresses all exceptions silently**: Line 351 catches bare `Exception` and returns `[]`. This means authentication failures, network DNS errors, and JSON parse errors are all silently dropped. If a provider returns an unexpected JSON structure, the user sees "0 models" with no indication of why.

- **WARNING — `ssl.create_default_context()` without certificate verification config**: `_ctx()` at line 60 creates a default SSL context, but some functions (e.g., `fetch_opencode_go`, `fetch_openrouter`, `fetch_google`) don't pass `context=_ctx()` to `urlopen`. The default `urlopen` behavior uses the system's default SSL context anyway, so this is consistent, but the inconsistent use of `context=_ctx()` across providers (some use it, some don't) suggests the intent was to standardize and some callers were missed.

- **WARNING — `fetch_codex()` returns hardcoded models with no validation**: Lines 301-315 hardcode model names. As of May 2026 these may or may not exist. The docstring notes this but there's no date stamp or version tag. Over time these will become stale.

- **WARNING — `fetch_lmstudio()` hardcoded URL `127.0.0.1:1234`**: Line 229. This only works if LM Studio is running locally on the default port. Configurable endpoint would be more robust.

- **WARNING — `run_model` uses `subprocess.run` with `capture_output=True` which buffers everything**: For long-running model calls (up to 300s timeout), no progress feedback is possible. This isn't a bug, but it means the user sees no output until the subprocess completes, which could be 5 minutes of silence.

- **SUGGESTION — `panels.json` race condition**: If two `select-panel.py` instances write `panels.json` simultaneously, data loss can occur. No file locking is implemented. Realistically, this is unlikely given the interactive nature, but noted for robustness.

- **SUGGESTION — `select-panel.py` interactive mode number selection uses displayed ordering**: Lines 173-178 index into `models` or `free_only` based on display position. If the user types numbers from one display mode (free-only) after switching to `all`, the numbers map to wrong models.

- **SUGGESTION — No model ID validation in `multi-chat.py`**: `load_panel` reads model IDs from `panels.json` but never validates they still exist or are reachable. A stale `panels.json` could reference deleted/unavailable models, and the failure would only surface at `hermes chat -q` subprocess time.

- **SUGGESTION — `multi-chat.py` `--timeout` default of 300s**: The timeout is set at the `subprocess.run` level, not per-provider. Some providers (OpenCode Go) may need more time, others (local LM Studio) should be faster. A per-provider timeout override would be useful.

### B. Consistency & Contradictions

- **WARNING — `panels.json` format mismatch risk**: In `select-panel.py`, `cmd_select_from_models` (line 246) and `cmd_select_interactive` (line 290) both write `data["active"] = name`, ensuring an `active` key. However, the documented example in the SKILL.md (lines 108-118) shows a `panels.json` format **without** the `active` key:
  ```json
  {
    "version": 1,
    "panels": { ... }
  }
  ```
  The SKILL.md example omits `"active"`, which would cause `multi-chat.py` to fail if it relies on `active` for default panel resolution. Looking at `multi-chat.py`, the `--panel` argument is **required** (`required=True`), so it doesn't use `active`. But the inconsistency between the SKILL.md example and actual code behavior could confuse users who edit `panels.json` manually.

- **WARNING — SKILL.md frontmatter says `version: 1.3.0` but `--delay` is documented as a v1.1.1+ workaround table entry**: The Common Pitfalls table refers to "multi-chat.py v1.1.1+" for the ARG_MAX workaround. This minor version reference is stale — the actual code version is 1.3.0 now. This isn't a contradiction per se, but the version reference in the pitfalls table should track the current version.

- **SUGGESTION — Provider list consistency**: The 12 providers in `PROVIDERS` list in `list-models.py` (lines 320-333), `PROVIDER_ORDER` in `select-panel.py` (line 40), and the SKILL.md table (lines 54-67) are all consistent. ✅

- **SUGGESTION — CLI interface consistency**: All three scripts' `--cwd` flags align with SKILL.md documentation. `--delay` is documented in both the help text and SKILL.md. `--panel`, `--prompt`, `--file` all match. ✅

- **SUGGESTION — SKILL.md references `templates/panels.default.json`**: This file is listed in the File Structure table (line 160) but wasn't part of the review. If it doesn't exist, the documentation points to a non-existent file.

### C. Real-World Operability

- **WARNING — `hermes chat -q` subprocess assumption**: The `run_model` function (line 95-110) constructs a command like `["hermes", "chat", "-q", prompt, "-m", model_id, "--provider", provider, "-Q", "--yolo", "--max-turns", str(turns)]`. This assumes `hermes` is on PATH and the CLI supports all these flags. In the Hermes Agent environment, the TUI agent process (`hermes`) may not have a `chat -q` subcommand, or it may behave differently when invoked as a subprocess (no interactive session, no tool access). The SKILL.md and memory notes confirm that `hermes chat -q` is the intended interface, but the `-Q` (quiet) and `--yolo` flags are not documented in the SKILL.md — they're implementation details that depend on the Hermes Agent CLI version.

- **WARNING — Windows `hermes` command resolution**: Lines 73-76 check `sys.platform == "win32"` but make no change — both branches set `hermes_cmd = "hermes"`. The WSL environment (the actual deployment per memory) uses Linux, so this is moot. But on native Windows, `hermes` might need to be `hermes.exe` or `hermes.bat` depending on installation method. The comment acknowledges this but doesn't solve it.

- **WARNING — `--cwd` is not passed through to `hermes chat -q`**: The `run_model` function constructs the `hermes chat -q` command but does not forward a `--cwd` or working directory argument. If the prompt references files via relative paths, the subprocess will use the parent process's cwd, not `args.cwd`. The subprocess uses `subprocess.run(cmd, ...)` without `cwd=`, meaning it inherits the Python process's cwd. If the user passed `--cwd /some/path` and the prompt contains relative file references, those won't resolve correctly.

- **SUGGESTION — Hardcoded `HERMES_HOME` path**: `list-models.py` line 34 uses `Path.home() / ".hermes"`. This works for the default profile but doesn't respect `HERMES_HOME` environment variable or profile-specific paths. Other Hermes Agent tooling may use a different home directory.

- **SUGGESTION — Temporary file path in `-q` instruction contains absolute path**: Line 89 embeds `tmpfile.name` (e.g., `/tmp/moa_prompt_XXXXXX.txt`) into the prompt instruction. If the hermes agent subprocess doesn't have `read_file` tool access or runs with different file access, this will fail silently (the model will try to read a file it can't access).

- **SUGGESTION — `ARG_MAX_THRESHOLD = 30000` is conservative**: Typical Linux ARG_MAX is 2MB+. The 30KB threshold triggers temp-file mode unnecessarily early for most systems. However, since it's a safety threshold and the temp-file mechanism works, this is purely an efficiency concern — it creates unnecessary temp files for 30-100KB prompts that would work fine as CLI args on most systems.

### D. Security & Safety

- **WARNING — API keys passed via `Authorization: Bearer` headers in `urllib.request`**: While this is standard HTTP auth, the keys are loaded from `.env` and `auth.json` files and used in cleartext HTTP requests. Lines 91-93 (Nous), 108-110 (OpenRouter), 136 (Google), etc. all construct Bearer tokens. For external APIs this is over TLS (https://) so it's fine, but the Google API key is transmitted as a URL query parameter (line 136: `?key={key}`), which means the key appears in server access logs, proxy logs, and browser history — a well-known anti-pattern.

- **SUGGESTION — No credential masking in output**: When `list-models.py` fails and prints error info, or when `select-panel.py` forwards stderr, there's no attempt to redact API keys from error messages. If a provider returns an error that echoes the request URL (including `?key=...`), it could leak to the console.

- **CRITICAL — Built-in `mixture_of_agents` warning is thorough and prominent**: The SKILL.md (lines 15-31) provides a very clear warning with:
  - Concrete cost ($5.80 actual damage)
  - Specific disable commands
  - Explicit "Never call" instruction
  - Alternative redirect to `multi-chat.py`
  
  This is well-done. The warning appears at the top of the skill, in the limitations section, and in the pitfalls table. ✅

- **SUGGESTION — No command injection vector**: The `subprocess.run(cmd, ...)` calls in both `list-models.py` (line 68) and `multi-chat.py` (line 114) pass arguments as lists, not through a shell. This correctly avoids shell injection. The only subprocess with user-controlled content is `hermes chat -q <prompt>`, which passes the prompt as a list element — safe from shell injection. ✅

- **SUGGESTION — `curl` dependency for OpenCode Go**: `fetch_opencode_go` (line 69) shells out to `curl`. If `curl` is not installed (uncommon but possible), this will fail with no graceful fallback. The comment says `urllib` returns 403, which is why `curl` is used — but no explanation for *why* curl works (likely a User-Agent or TLS fingerprint issue). This could be replaced with `urllib.request` + custom headers.

- **SUGGESTION — `gh auth token` subprocess in `fetch_copilot`**: Line 243 runs `gh auth token` to obtain a GitHub token. This command may produce interactive prompts or browser-based auth flows if the token is expired. With `timeout=5`, this could fail silently. The token itself is not leaked again after being used in the Authorization header.

---

## Summary Score: **7.5 / 10**

**Strengths**:
- Solid overall architecture: 3 scripts with clear separation of concerns
- Comprehensive provider coverage (12 providers)
- Good error handling for the main failure modes (timeout, subprocess failure, empty results)
- The `--delay` rate-limiting mechanism works correctly, even if the lock-sleep pattern is suboptimal
- Temp-file cleanup is properly handled with `finally` block
- The SKILL.md documentation is thorough, with clear workflow, pitfalls table, and safety warnings
- `panels.json` schema is simple and consistent between writer and reader
- No command injection vectors (all subprocess calls use list args)

**Weaknesses**:
- `time.sleep()` inside `threading.Lock` serializes execution unnecessarily (correct result, poor throughput)
- `_fmt()` is duplicated across two files
- `--cwd` is not forwarded to the `hermes chat -q` subprocess working directory
- Google API key leaked in URL query parameter
- The Windows `hermes` command resolution is a no-op (dead code)
- Exceptions are squelched too aggressively in `load_all_models` — no diagnostic logging
- The `--models` format uses `:` as a separator, which breaks for model IDs containing `:` (unlikely but possible)
- The temp-file workaround for large prompts leaks the implementation detail that hermes needs `read_file` tool access


---

### ✅ mimo-v2.5-pro (`opencode-go` — 87.7s)

Here is the full code review.

=======================================================================
                    HERMES-FAKE-MOA CODE REVIEW
=======================================================================

## A. Script Logic & Potential Bugs

**multi-chat.py — tmpfile cleanup on exceptions**

- **SUGGESTION**: The `finally` block in `run_model()` (line 174-180) correctly
  handles cleanup on TimeoutExpired and generic Exception. This is solid.
  However, if the process is killed by signal (SIGKILL/SIGTERM), the `finally`
  block still runs in CPython, so this is safe in practice.

- **WARNING**: In the large-prompt branch (line 81-86), `NamedTemporaryFile`
  is created with `delete=False`. If an exception occurs between file creation
  and the `subprocess.run` call (e.g. during `tmpfile.write(prompt)`), the
  `finally` block will still attempt `os.unlink`, which is correct. No leak.

**multi-chat.py — delay implementation**

- **WARNING** (minor): The `submit_with_delay` function (line 197-208) holds
  `submit_lock` while calling `time.sleep(wait)`. This blocks ALL other
  threads from even checking their delay during that sleep. With 5 models on
  the same provider and delay=1.0, the lock is held for 1+1+1+1 = 4 seconds
  serially. This is functionally correct but suboptimal — the delay enforces
  per-provider serialization (which is the intent), but models on DIFFERENT
  providers are also blocked from submitting during that sleep. A more
  granular per-provider lock would allow cross-provider parallelism.

- **SUGGESTION**: The delay logic only tracks by provider name. If two
  different panels have the same provider but different API keys (not
  currently supported), this would over-throttle. Low priority.

**multi-chat.py — global mutation**

- **WARNING**: Lines 288, 301-302 mutate module globals `MAX_TURNS` and
  `TIMEOUT` from `main()`. This is safe for a CLI script (single invocation),
  but is a code smell. If this module were ever imported as a library, it
  would cause subtle bugs.

**list-models.py — env file parsing**

- **WARNING**: The `read_env()` function (line 39-47) does a naive
  `split("=", 1)`, which handles values containing `=` correctly (via the
  `1` limit). However, it does NOT handle quoted values (`KEY="value with
  spaces"`) or inline comments (`KEY=value # comment`). The quotes would
  become part of the value. This matches typical `.env` simple format but
  could cause API key mismatches if the user's `.env` has quoted values.

**list-models.py — fetch_nous exception handling**

- **WARNING**: `fetch_nous()` (line 87-101) does NOT have a try/except block
  around the `urllib.request.urlopen` call, unlike most other fetch functions.
  An HTTP error (401, 403, 500) would raise `urllib.error.HTTPError` and
  propagate up. The outer `load_all_models()` does catch this (line 351), so
  it won't crash, but the error message will be swallowed silently. All other
  fetchers wrap their calls.

**select-panel.py — JSON parsing fallback**

- **SUGGESTION**: The fallback JSON parsing in `fetch_models()` (line 84-88)
  looks for a line starting with `[` to find the JSON array. This is clever
  but fragile — if a stderr line somehow leaks into stdout and starts with
  `[`, it would break. In practice, `capture_output=True` separates them, so
  this is low risk.

**multi-chat.py — stdin blocking**

- **WARNING**: Line 309-310 reads from stdin if not a tty. This is correct
  for piping, but if the agent runs this script without `--prompt` or `--file`
  and stdin is somehow connected but empty, it will block indefinitely.
  There's no timeout on stdin.read(). Low risk in practice since the agent
  always provides `--prompt` or `--file`.

**Python syntax / imports**

- No syntax issues found. All type hints use `dict[str, str]` (Python 3.9+
  syntax) and `str | None` (Python 3.10+). The SKILL.md correctly states
  Python 3.10+ as a prerequisite.

=======================================================================

## B. Consistency & Contradictions

**Provider names**

- **All consistent** across list-models.py (PROVIDERS list, line 320-333),
  select-panel.py (PROVIDER_ORDER, line 40), multi-chat.py (reads from
  panels.json), and SKILL.md (table, line 54-67). All 12 provider IDs match.

**panels.json format**

- select-panel.py writes: `{"version": 1, "active": "name", "panels": {"name": [...]}}`
- multi-chat.py reads: `data.get("panels", {})[name]`
- SKILL.md documents: `{"version": 1, "panels": {...}}` (no "active" key shown)
- **WARNING**: The SKILL.md manual-edit example (line 108-118) omits the
  `"active"` key. While `multi-chat.py` doesn't use `active` (it takes
  `--panel` explicitly), this is a minor documentation inconsistency.
  `select-panel.py` always sets `"active"` on save.

**Version vs feature set**

- Version 1.3.0 in SKILL.md frontmatter. The feature set (12 providers,
  --delay, large-prompt workaround, --cwd threading, comparison table)
  is consistent with a 1.x mature release. No contradictions found.

**SKILL.md says "3 models simultaneously, maximum 5"**

- **WARNING**: The code in `select-panel.py` enforces min=2, max=5
  (lines 134, 150-152). SKILL.md says "Default: 3 models simultaneously"
  but there is no default of 3 enforced anywhere — the interactive mode
  just lets you pick 2-5. The "3" is a recommendation, not enforced.
  This is slightly misleading in the docs.

**SKILL.md says `--delay` prevents 429s**

- The implementation (line 197-208 of multi-chat.py) delays between models
  on the SAME provider, which is correct. The SKILL.md documentation
  (line 138) says "If multiple models share the same provider" which
  accurately describes the behavior.

=======================================================================

## C. Real-World Operability

**`hermes chat -q` subprocess calls**

- **CRITICAL**: The `hermes chat -q` command is invoked via subprocess.
  This requires `hermes` to be on PATH. In a Hermes Agent environment, this
  is typically the case. However:
  - The script uses bare `"hermes"` (line 73-76), which works on Linux/macOS
    if the binary is on PATH.
  - On Windows (line 74-76), the code checks `sys.platform == "win32"` but
    then still uses `"hermes"` — the comment mentions `hermes.bat` but
    doesn't actually try it. Windows `.bat` files are found via PATH
    automatically by `subprocess.run`, so this works, but the dead code
    is misleading.
  - **WARNING**: If running in WSL (the user's environment), `sys.platform`
    is `"linux"`, not `"win32"`, so the Windows branch is never taken.
    Correct for WSL.

**Hardcoded paths**

- No hardcoded absolute paths found. All paths are derived from:
  - `Path(__file__).resolve().parent.parent` (SKILL_DIR)
  - `Path.home() / ".hermes"` (HERMES_HOME)
  - `Path.cwd()` or `--cwd` argument
  - These are all portable.

**`--cwd` threading**

- **Properly threaded** in select-panel.py: `main()` passes `args.cwd` to
  all `cmd_*` functions.
- **Properly threaded** in multi-chat.py: `main()` passes `args.cwd` to
  `load_panel()` and `save_results()`.
- Both `resolve_panels_file()` functions are duplicated (identical code in
  both scripts). This is a minor DRY violation but acceptable for standalone
  scripts.

**`hermes chat -q` with `--yolo` flag**

- Line 99 and 108 pass `--yolo` which likely enables auto-approve for tool
  calls. Combined with `--max-turns`, this allows the sub-agent to use tools
  (like `read_file` for the large-prompt workaround) without user
  interaction. This is the correct pattern for autonomous orchestration.

**The `-Q` flag**

- Lines 99 and 108 pass `-Q` (quiet mode). This suppresses hermes' own
  progress output, making stdout clean for result parsing. Good design.

=======================================================================

## D. Security & Safety

**Credential leakage**

- **No credentials are hardcoded** in any script. All API keys are read from
  `~/.hermes/.env` or `~/.hermes/auth.json` at runtime.
- The `fetch_google()` function (line 136) puts the API key in a URL query
  parameter (`?key={key}`). This is the standard Google AI Studio pattern,
  but the key could appear in server logs. Not a script-level issue.

**Built-in MoA warning**

- **Adequately clear**: SKILL.md lines 15-40 have a prominent CRITICAL
  warning section with absolute rules, the disable command, and the cost
  damage amount ($5.80). The warning appears before any usage instructions.
  This is thorough.

**Command injection**

- **No injection vectors found**. All subprocess calls use list arguments
  (not shell=True). The prompt is passed as a list element to
  `subprocess.run`, so shell metacharacters in the prompt are not
  interpreted.
- The temp file path (line 89: `tmpfile.name`) is generated by Python's
  `tempfile` module, not user-controlled. Safe.
- **SUGGESTION**: The `--file` argument (line 306) is passed directly to
  `Path(args.file).read_text()`. If the file doesn't exist, Python raises
  `FileNotFoundError` which is uncaught. This would produce an ugly
  traceback instead of a user-friendly error message. Consider wrapping
  in try/except.

**Result file writing**

- `save_results()` writes to `{cwd}/results/` with model names in filenames
  (line 233). Model IDs can contain `/` (e.g., `deepseek/deepseek-v4-flash`)
  which is replaced with `_` via `.replace('/', '_')`. This prevents
  directory traversal. Safe.

=======================================================================

## Summary of Findings

CRITICAL:  0
WARNING:   7
SUGGESTION: 4

Key warnings:
1. delay lock held during sleep blocks cross-provider parallelism
2. fetch_nous() lacks try/except (handled by outer caller, but inconsistent)
3. .env parser doesn't handle quoted values
4. SKILL.md "Default: 3 models" is misleading (not enforced)
5. SKILL.md manual-edit example omits "active" key
6. Global mutation of MAX_TURNS/TIMEOUT
7. Windows hermes_cmd branch is dead code

Overall quality score: 8/10

The codebase is well-structured, defensively coded, and production-ready
for its intended use case (Hermes Agent CLI orchestration). The delay
implementation is correct in intent but could be more concurrent. Error
handling is comprehensive with one inconsistency (fetch_nous). The SKILL.md
documentation is thorough with clear warnings about the built-in MoA pitfall.
The temp-file workaround for large prompts is properly implemented with
cleanup in all code paths. No security issues found.


---

### ❌ minimax-m2.7 (`opencode-go` — 25.4s)

```
API call failed after 3 retries: HTTP 404 — Not Found | opencode
```
**Error**: `Loading weights:   0%|          | 0/152 [00:00<?, ?it/s]
Loading weights:  75%|███████▌  | 114/152 [00:00<00:00, 1119.65it/s]
Loading weights: 100%|██████████| 152/152 [00:00<00:00, 1355.05it/s]

Batc`

---

