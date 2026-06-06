# Architecture: how agent-sandbox is built inside

This document explains how the whole tool is put together: what each piece is,
where it lives, and what it is for. It is written for someone who has never seen
the code before. We go slowly and use everyday pictures.

If you only remember one thing, remember this sentence:

> The tool turns **the words you type** into **a settings object**, turns that
> object into **one long command line**, and then **runs that command line**.

Everything else is detail about those four steps.

## The big picture: an assembly line

Think of a small factory with an assembly line. A raw order comes in one end, it
moves along the belt, each station adds something, and a finished product comes
out the other end. Our "product" is a running sandbox.

```
  what you type                                                 a running
  on the command          a settings        one long           sandboxed
  line                    object             command line       program
  ------------            ------------       ------------       ------------
  isolate run    ──▶      SandboxConfig ──▶  systemd-run ... ──▶  your command,
  --no-network            (one tidy           bwrap ...           safely boxed in
  -- claude               blueprint)          -- claude
        │                      │                    │                  │
     cli.py               profiles.py          sandbox.py          the OS runs it
   (reads input)         (decides settings)   resources.py        (cli.py launches)
                          config.py            (build the line)
                          paths.py
```

Each station on the belt is one Python file. The next sections explain each one.

## The single most important thing: the SandboxConfig

Before touching any file, understand the object that travels down the belt.

`SandboxConfig` (defined in `config.py`) is a plain box of settings. It is the
**one tidy blueprint** that answers every question the sandbox needs: which folder
is writable, where the fake home is, which system files to expose, is the network
on, what are the CPU and memory caps, and what command to run.

Real life picture: it is the **order ticket** in a kitchen. The waiter writes the
whole order on one ticket. The cooks never talk to the customer; they just read
the ticket. In our code, the early files **write the ticket**, and the later
files **read the ticket**. Nothing downstream has to guess what the user wanted,
because it is all on the ticket.

This matters because it keeps the design simple: one clear handoff point.

## Two kinds of code: "thinkers" and "doers"

The single most important design choice in this project is splitting the code into
two kinds:

- **Thinkers (pure functions).** These only take information in and give an answer
  back. They never change anything in the real world: no files created, no
  programs launched, no reading of the live machine. Given the same input, they
  always give the same output.
- **Doers (side effects).** These actually touch the world: read the real machine,
  create folders, and launch the sandbox.

Real life picture: an **architect** draws a blueprint (pure thinking; drawing a
plan changes nothing in the world), while a **builder** pours the concrete (a real
effect you cannot undo). We keep the architects and the builders in separate
rooms.

Why bother? **Testing.** Thinkers are trivial to test: hand them input, check the
output, no real sandbox needed. That is why the test suite is fast and why we can
practice test-first development comfortably. The few "doers" are kept thin and are
given their tools from outside (more on that in the testing section), so even they
can be tested without touching the real system.

In this project:

- Thinkers: `config.py`, `paths.py`, `profiles.py`, `sandbox.py`, `resources.py`.
- Doers: `cli.py` and `doctor.py` (the edges), plus `__main__.py`.

## A tour of every file (what, where, what for)

All source lives under `src/isolate/`. Here is each file, in the order the
assembly line uses it.

### `config.py` - the blueprint and the rule checker

- **What it is:** defines the `SandboxConfig` blueprint, the built-in default
  settings (`BUILTIN_DEFAULTS`), and small validators (`validate_memory`,
  `validate_cpus`) that reject nonsense like `--memory loads`.
- **Where:** `src/isolate/config.py`.
- **What for:** it is the shared vocabulary. Almost every other file imports the
  `SandboxConfig` type from here. Think of it as the **blank order ticket** plus
  the rule that says "an order must make sense".
- **Thinker or doer:** thinker (pure data and checks).

### `paths.py` - which parts of the system to hand over

- **What it is:** decides which read-only system folders and files the sandbox
  needs (`system_mounts`), handles the "merged /usr" symlink quirk, and spots
  dangerous grants like your `~/.ssh` (`find_sensitive`).
- **Where:** `src/isolate/paths.py`.
- **What for:** the sandbox starts as an empty room. This file is the **packing
  list** of safe, read-only system items (libraries, certificate files) to place
  in the room so normal programs can even start.
- **Thinker or doer:** thinker. It can inspect a folder layout, but you can hand
  it a fake root, so tests never depend on the real machine.

### `profiles.py` - the waiter who writes the final ticket

- **What it is:** reads the config files, merges the layers (built-in defaults,
  then your global file, then the project file, then the command-line flags),
  and produces the finished `SandboxConfig`. Key function: `resolve(...)`.
- **Where:** `src/isolate/profiles.py`.
- **What for:** this is where "what the user wants" becomes "one exact blueprint".
  It expands `~` and relative paths into absolute ones and attaches the system
  packing list from `paths.py`.
- **Thinker or doer:** thinker. It reads config files you point it at, but it
  launches nothing and changes nothing.

### `sandbox.py` - builds the bubblewrap command

- **What it is:** turns a `SandboxConfig` into the actual `bwrap ...` argument
  list (`build_bwrap_args`), and wraps that in resource limits when asked
  (`build_command`).
- **Where:** `src/isolate/sandbox.py`.
- **What for:** this is the **recipe writer**. It reads the ticket and writes out,
  step by step, the long command that builds the safe room and runs your program
  inside it.
- **Thinker or doer:** thinker. It returns a list of strings; it does not run
  them. (Running them is the job of `cli.py`.)

### `resources.py` - adds the CPU and memory limits

- **What it is:** builds the `systemd-run --user --scope ...` prefix that caps CPU
  and memory (`systemd_scope_args`, `cpus_to_quota`), and checks whether systemd
  is even available (`is_systemd_available`).
- **Where:** `src/isolate/resources.py`.
- **What for:** bubblewrap builds the walls but does not ration resources. This
  file is the **portion-control** station. If systemd is missing, it steps aside
  gracefully so the sandbox still runs (just without caps).
- **Thinker or doer:** mostly thinker (building the prefix is pure); the single
  "is systemd here?" check is the one small peek at the real machine, and it is
  isolated so callers can fake it.

### `cli.py` - the front desk (a doer)

- **What it is:** reads the command line, splits your isolate flags from the inner
  command at the `--` fence (`split_command`), turns flags into overrides
  (`build_overrides`), calls `profiles.resolve` and `sandbox.build_command`, warns
  about risky grants, and finally launches the sandbox (or prints it for
  `--dry-run`).
- **Where:** `src/isolate/cli.py`.
- **What for:** it is the **only place that talks to the user and to the operating
  system**. It is kept deliberately thin: it wires the thinkers together and then
  pulls the trigger.
- **Thinker or doer:** doer. This is where real effects happen: creating the fake
  home folder and replacing the process with the sandbox (`os.execvp`).

### `doctor.py` - the pre-flight checklist (a doer)

- **What it is:** runs small health checks (is bubblewrap installed, are user
  namespaces allowed, is systemd available) and prints a friendly report with
  fix-it commands.
- **Where:** `src/isolate/doctor.py`.
- **What for:** like the **dashboard lights** before a drive. Each check is a tiny
  function that takes its "probe" as an argument, so tests feed it fake answers.
- **Thinker or doer:** doer at the edge, but built from easily-faked small checks.

### `__main__.py` and `__init__.py` - the small glue

- `__main__.py` lets you run the tool with `python -m isolate`.
- `__init__.py` marks the folder as a package and holds the version number.

## Following one real command from start to finish

Let us trace exactly what happens when you run:

```
isolate run --no-network -- claude
```

1. **Split at the fence.** `cli.split_command` cuts the line at `--`. Left side:
   `run --no-network` (settings). Right side: `claude` (the command to run).
2. **Parse the settings.** `cli.build_arg_parser` reads `--no-network` and friends.
   `cli.build_overrides` packs them into a small overrides dict
   (here: `{"network": False, ...}`).
3. **Write the ticket.** `cli` calls `profiles.resolve`. That function:
   - starts from `BUILTIN_DEFAULTS` (in `config.py`),
   - layers your config files on top (if any),
   - layers your command-line overrides on top of that,
   - validates the values (`validate_memory`, `validate_cpus`),
   - turns `.`, `~`, and relative paths into absolute paths,
   - asks `paths.system_mounts` for the read-only system packing list,
   - and returns a finished `SandboxConfig`. The ticket is now complete.
4. **Safety warning.** `cli` calls `paths.find_sensitive` to check if you granted
   anything risky (like your whole home). If so, it prints a warning but obeys you.
5. **Write the recipe.** `cli` calls `sandbox.build_command`, which calls
   `build_bwrap_args` to produce the `bwrap ...` line, and (if caps were asked for
   and systemd is present) prepends the `systemd-run ...` scope from `resources`.
6. **Run it (or print it).** If `--dry-run`, `cli` just prints the command. If not,
   `cli` creates the fake home folder and then `os.execvp` replaces itself with the
   sandbox command. Your `claude` now runs inside the safe room.

That is the entire journey: input becomes a ticket, the ticket becomes a recipe,
the recipe is cooked.

## How the final command is built: an onion of wrappers

The command we run is layers wrapped around layers, like an onion (or a set of
nesting dolls). From the outside in:

```
systemd-run --user --scope ...   <- outer layer: sets CPU and memory limits
  bwrap ...                       <- middle layer: builds the safe room (walls)
    claude                        <- inner core: your actual program
```

Each layer only knows about the one inside it. systemd wraps bwrap; bwrap wraps
your program. If you remove the limits (no `--memory`/`--cpus` and the defaults
turned off), the outer onion layer simply is not there, and `bwrap` becomes the
outermost command. You can see the whole onion any time with `--dry-run`.

## How settings are decided (the layer cake)

Settings come from four stacked layers, where higher layers win: built-in
defaults, then your global file, then the project file, then the flags you typed.
This is explained with examples in [usage.md](usage.md#where-settings-come-from-the-layer-cake).
The code that performs this stacking is `profiles.resolve_profile_dict` and
`profiles.apply_cli_overrides`.

## The testing architecture (why it mirrors the code)

The tests live in `tests/` and come in two flavors that match the two kinds of
code:

- **Pure tests (fast).** Most tests check the "thinkers". They hand a function
  some input and assert on the output. No sandbox is launched. Run them with
  `pytest -m "not integration"`. They finish in a fraction of a second, which is
  what makes test-first development pleasant.
- **Integration tests (real).** A handful in `tests/integration/` launch a real
  `bwrap` to prove the walls actually hold (writes inside work, `/usr` is
  read-only, the real home is invisible, the network switch is obeyed). They are
  marked `integration` and skip automatically if `bwrap` is missing.

### The trick that keeps the "doers" testable: seams

Even the doers avoid touching the real machine during tests, thanks to
**dependency injection**, a fancy phrase for a simple idea: "instead of reaching
out for a tool yourself, accept the tool as an argument, so a test can hand you a
fake one."

Real life picture: a recipe that says "use the oven in front of you" can be tested
with a toy oven. A recipe that says "drive to my specific kitchen and use my oven"
cannot. We always write the first kind.

Examples of these seams in the code:

- `profiles.resolve(..., system_mounts_fn=...)` lets tests pass a fake system
  layout instead of reading the real `/`.
- `doctor.check_bwrap(which=...)`, `check_user_namespaces(read_sysctl=...)`, and
  `check_systemd(available_fn=...)` each take their probe as an argument.
- `sandbox.build_command(config, systemd_available=...)` takes the systemd answer
  as a plain argument, so tests can try both "present" and "missing" without
  needing systemd.

## How to add a new feature (where would it go?)

Use the assembly line to decide where new code belongs:

- **A new setting (for example a disk-space cap).** Add the field to
  `SandboxConfig` in `config.py`, add validation there, teach `profiles.resolve`
  to fill it from config/flags, and teach `sandbox.py` or `resources.py` to use
  it. Add a flag in `cli.py`. Write the pure tests first.
- **Turning on seccomp** (see [primers/seccomp.md](primers/seccomp.md)). This is a
  new bwrap flag, so it belongs in `sandbox.build_bwrap_args`, driven by a new
  config field. The filter file handling would be a small new helper.
- **A second backend (for example podman instead of bubblewrap).** Keep
  `SandboxConfig` as the shared ticket, and add a new builder module next to
  `sandbox.py` that reads the same ticket but emits a podman command. `cli.py`
  would choose the builder based on a setting.

The rule of thumb: decisions and command-building go in the **thinkers**;
anything that reads the live machine or launches a process goes in the **doers**
(`cli.py` / `doctor.py`), behind an injectable seam.

## Error handling and safety defaults

- Bad input (an unknown profile, a malformed memory value) raises a `ConfigError`
  from `config.py`/`profiles.py`. `cli.py` catches it and prints a clear message,
  then exits non-zero. The user never sees a raw stack trace for normal mistakes.
- If systemd is missing, the tool does not crash; it drops the resource caps and
  warns. Walls before luxuries.
- The filesystem model is **deny by default**: nothing is shared unless named, so
  a forgotten grant fails safely instead of leaking.

## Directory map

| Path | Role |
| --- | --- |
| `src/isolate/config.py` | The `SandboxConfig` blueprint, defaults, validation |
| `src/isolate/paths.py` | System packing list, symlink handling, risky-grant check |
| `src/isolate/profiles.py` | Read config files, merge layers, resolve final config |
| `src/isolate/sandbox.py` | Build the `bwrap` command (and wrap with limits) |
| `src/isolate/resources.py` | Build the `systemd-run` scope for CPU/memory limits |
| `src/isolate/cli.py` | Parse input, wire it together, launch the sandbox |
| `src/isolate/doctor.py` | Pre-flight health checks |
| `tests/` | Fast pure tests |
| `tests/integration/` | Real-bubblewrap tests |
| `docs/` | This file, usage, security model, and the primers |

## Where to go next

- New to the underlying ideas? Read the [primers](primers/) (isolation, namespaces,
  cgroups, bubblewrap, seccomp).
- Want to use the tool? See [usage.md](usage.md).
- Want the honest safety boundaries? See [security-model.md](security-model.md).
- Working on the code? See [AGENTS.md](../AGENTS.md) for the engineering rules.
