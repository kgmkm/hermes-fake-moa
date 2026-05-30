# Large Prompt Workaround (ARG_MAX Limit)

## Problem

`hermes-fake-moa`'s `multi-chat.py` internally calls `hermes chat -q "prompt"`.
The `-q` argument is passed via the command line, so it is subject to the OS ARG_MAX limit
(typically 128KB on Linux, even smaller on WSL).

Prompts larger than ~30KB fail with:
```
[Errno 7] Argument list too long: 'hermes'
```

`hermes chat` has **no**:
- `--prompt-file` / `--file` option (does not exist)
- stdin prompt reading (`-q` is required; interactive mode does not work for this purpose)

## Verified Workarounds

### Method A: multi-chat.py auto temp-file mode (v1.1.1+, recommended)

`multi-chat.py` v1.1.1 automatically detects prompts exceeding `ARG_MAX_THRESHOLD`
(default 30,000 characters) and performs the following:

1. Writes prompt content to a temp file (`/tmp/moa_prompt_*.txt`)
2. Passes only a short instruction via `-q` ("read_file /tmp/moa_prompt_XXXXX.txt ...")
3. The agent reads the actual prompt using the `read_file` tool, then responds
4. `--max-turns` is automatically incremented by +2 (headroom for read_file + answer)
5. Temp file is auto-deleted after session ends (in `finally` block)

**Use `multi-chat.py` as usual:**
```bash
python3 scripts/multi-chat.py --panel my-panel --file /tmp/large_prompt.txt --cwd /path/to/project
```

This completely bypasses the ARG_MAX limit while retaining all parallel dispatch and result collection features.

**Threshold adjustment**: Change the `ARG_MAX_THRESHOLD` constant in `scripts/multi-chat.py`
(default 30000). The default is safe for WSL environments.

### Method B: Have the agent read files manually (pre-v1.1.0 approach)

Include only "file path list" and "evaluation criteria" in the prompt,
and let the agent's `read_file` tool handle the actual text reading.

**Prompt template**:
```
You are a [role]. Read all of the following files and perform [task].

[File path list]

[Project info / evaluation criteria / response format]
(Meta info and instructions only — no body text)
```

**Example** (reader-perspective evaluation):
```
/mnt/y/novel/project/manuscript/chapter_01.md
/mnt/y/novel/project/manuscript/chapter_02.md
...
/mnt/y/novel/project/manuscript/chapter_11.md

Read all of these files, then evaluate them from the following perspectives...
```

This prompt fits within ~3.3KB and works without issues.

### Running commands

Launch each model individually with `hermes chat -q` in the background:
```bash
hermes chat -q "$(cat instruction.txt)" \
  -m glm-5.1 --provider opencode-go -Q --yolo --max-turns 15 &
hermes chat -q "$(cat instruction.txt)" \
  -m mimo-v2.5-pro --provider opencode-go -Q --yolo --max-turns 15 &
hermes chat -q "$(cat instruction.txt)" \
  -m kimi-k2.6 --provider opencode-go -Q --yolo --max-turns 15 &
```

Estimate `--max-turns` as: number of files to read + response generation
(e.g., 11 files + 1 answer = minimum 12 turns → set 15).

### Notes

- v1.1.1+ recommends Method A (multi-chat.py auto temp-file mode). Simply specifying a large prompt file with `--file` handles everything automatically.
- Method B (manual `hermes chat` parallel launch) is the pre-v1.1.0 workaround. Still valid, but result collection is manual.
- No file lock contention occurs since all models read common files (read-only).
- In Method B, results must be collected manually from each model's stdout (not auto-saved to `results/`).

## Considered and Rejected Approaches

| Approach | Result | Reason |
|----------|--------|--------|
| multi-chat.py with stdin pipe (`input=prompt`) | ❌ | `hermes chat` without `-q` enters interactive mode; reads stdin but exits without generating a response |
| multi-chat.py with temp file + read_file instruction (**adopted in v1.1.1**) | ✅ | Only a short instruction via `-q`; agent reads actual prompt via tool. ARG_MAX fully bypassed |
| Split prompt into chunks | △ | Does not work for tasks requiring full-pass reading (reader-perspective evaluation, etc.) |
| Delegate to sub-agent via `delegate_task` | △ | Sub-agents cannot use different models (inherit parent), and result collection is complex |
