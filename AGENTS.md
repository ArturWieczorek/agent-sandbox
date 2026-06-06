# AGENTS.md - principles and lessons for working on this repo

This file is the standing rulebook for anyone (human or AI) working on this
project. It outlives any single chat session. Read it before making changes.

For personal writing-style and behavior rules (no em or en dashes, no AI
authorship on commits or comments, very simple explanations), see `CLAUDE.md` in
this repo. Those rules also apply here.

## Basic principles

1. **Test-first, always (TDD).** For every change: write a failing test first,
   then write the minimum code to make it pass. No production change lands without
   a test that would fail without it.
2. **Run the whole suite on every change.** After each change, run `pytest`. Keep
   the fast suite (`pytest -m "not integration"`) green at all times. Run the full
   suite (with real bubblewrap) before calling a piece of work done.
3. **Default-deny, least privilege.** The sandbox starts empty and we add only
   what is named. Never widen access "just in case". Prefer the smallest grant
   that makes the task work.
4. **Keep the core pure.** The command builders (`sandbox.py`, `resources.py`) are
   pure functions: config in, argument list out, no side effects. Side effects
   (creating folders, launching, reading the real machine) live at the edges
   (`cli.py`, `doctor.py`) and are injected so they can be faked in tests.
5. **Be honest about security.** Never claim more safety than the tool gives. The
   bubble is a strong hotel room, not a bank vault. Document limits plainly (see
   `docs/security-model.md`).
6. **Write docs in very simple language.** Assume the reader is new to the topic.
   Use short sentences and real life analogies. Update the relevant doc in the
   same change that alters behavior.
7. **Plain commits, no AI attribution.** Do not add "Co-Authored-By" or "Generated
   with" lines, and do not sign comments as written by an AI.

## How the pieces fit (quick map)

For a detailed, plain-language tour of the design, see
[docs/architecture.md](docs/architecture.md).

- `config.py` - the resolved settings object, defaults, and value validation.
- `paths.py` - which host paths form the read-only system base; symlink handling;
  spotting dangerous grants.
- `sandbox.py` - pure builders: `build_bwrap_args` and `build_command`.
- `resources.py` - the systemd scope that applies CPU/memory limits.
- `agents.py` - recipes for known agents (claude, gemini): the command to run and
  the read grants they need.
- `profiles.py` - load config files, merge layers, resolve to a `SandboxConfig`.
- `cli.py` / `doctor.py` - the edges: parse input, prepare the system, launch,
  and run health checks.

## Lessons learned (append new ones at the top)

A running log of non-obvious things we discovered. Each entry: what we expected,
what actually happened, and what to do about it.

### Agents live in your home, so they are invisible by default

- **Expected:** `isolate run -- claude` would just work.
- **Reality:** claude and gemini are installed under the user's home (for example
  `~/.local/share/claude` and `~/.nvm/...`), which the bubble never mounts, so the
  command is "not found" inside. Claude is a self-contained binary; gemini is a
  node app that also needs the Node.js runtime mounted.
- **Apply:** use the `--agent` recipes in `agents.py`, which grant exactly the
  agent's files (and node for gemini). Run node agents as `node <script>` rather
  than relying on a shebang or PATH inside the sandbox.

### Writes to unbound paths are ephemeral, not blocked

- **Expected:** writing to a path we did not share (like `/etc/foo`) would fail
  with "permission denied".
- **Reality:** it often **succeeds**, but only on the sandbox's throwaway
  in-memory root. The real host file is never touched, and the change vanishes
  when the sandbox closes. Only true read-only binds (like `/usr`) reject writes
  with "read-only file system".
- **Apply:** when proving "the real system is safe", test two distinct things: a
  read-only bind rejects writes, AND the real host file does not exist afterward.
  Do not assume an unbound write returns an error.

### bubblewrap does not limit CPU or memory

- **Expected:** the sandbox tool would also cap resources.
- **Reality:** bubblewrap only builds the file/process/network walls. Resource
  caps come from cgroups, which we drive via `systemd-run --user --scope`.
- **Apply:** keep the two concerns separate in code and docs. If systemd is
  missing, degrade gracefully (run without caps) and warn, rather than failing.

### Merged-/usr means symlinks, not extra binds

- **Expected:** we could just `--ro-bind` `/usr`, `/bin`, `/lib`, etc.
- **Reality:** modern distros make `/bin`, `/lib`, `/lib64` symlinks into `/usr`.
  Binding both the target and its symlink alias causes errors or double mounts.
- **Apply:** detect symlinks and recreate them with `--symlink` instead of binding
  them (see `paths.system_mounts`). Bind only the real directories.

### Wipe the environment, then add back the minimum

- **Expected:** inheriting the environment is convenient.
- **Reality:** environment variables commonly hold secrets (API tokens). Passing
  them in silently defeats the point of hiding the home folder.
- **Apply:** always `--clearenv` and then set back only `HOME`, `PATH`, and `TERM`.
