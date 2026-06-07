# Using isolate

This page explains every option in plain language, then shows worked examples.

## The shape of a command

```
isolate run [bubble options] -- <the command to run inside>
```

The `--` (two dashes alone) is a fence. To its **left** you describe the bubble.
To its **right** you write the actual program and its arguments. Everything on
the right is passed through untouched, so the program sees its own flags, not
isolate's.

Think of it like dropping a worker and their tools through a hatch: the left side
is you setting up the room, the `--` is the hatch, and the right side is the
worker plus the toolbox they carry in.

## The two subcommands

### `isolate doctor`

Runs a quick health check of your machine and prints a simple report. It changes
nothing. Each line is either `[PASS]` or `[FAIL]`, and every failure comes with
the exact command to fix it. Run this first if anything is not working.

### `isolate run`

Runs a command inside the bubble. The options below all belong to `run`.

## Options for `run`

| Option | Plain meaning |
| --- | --- |
| `--agent NAME` | Run a known agent (`claude` or `gemini`) and auto-grant what it needs. |
| `--login` | With `--agent`, also share the agent's saved login from your home. |
| `--profile NAME` | Use a named bundle of settings. Default is `default`. |
| `--no-network` | Cut off the internet completely (air-gapped). |
| `--network` | Force the internet on (this is already the default). |
| `--memory SIZE` | Memory cap, like `4G` or `512M`. The program cannot exceed it. |
| `--cpus N` | CPU cap in cores, like `2` or `0.5` (half a core). |
| `--allow-write PATH` | Let the bubble also write to PATH. Repeatable. |
| `--allow-read PATH` | Let the bubble also read PATH (read-only). Repeatable. |
| `--env KEY=VALUE` | Set an environment variable inside the bubble. Repeatable. |
| `--home PATH` | Use PATH as the throwaway fake home. |
| `--config FILE` | Read one more config file, layered on top of the rest. |
| `--dry-run` | Print the command that would run, but do not run it. |

## Running a known agent (claude, gemini)

The agents you want to sandbox (Claude Code, the Gemini CLI) are installed inside
your home folder. The bubble never mounts your home, so they are invisible by
default, and a bare `isolate run -- claude` fails with "not found". This is the
deny-by-default rule doing its job.

`--agent` is the shortcut that fixes this for known tools. It knows where each
agent lives and grants exactly the read-only paths it needs (the agent's own
files and, for node-based agents, the Node.js runtime), then runs it.

```bash
# Run Claude Code, sandboxed to the current project.
isolate run --agent claude

# Run the Gemini CLI the same way.
isolate run --agent gemini

# Pass arguments through to the agent (everything after -- goes to it).
isolate run --agent claude -- --version
isolate run --agent gemini -- chat
```

### The login trade-off (`--login`)

With the throwaway fake home, the agent does not see its saved login, so it may
ask you to sign in again each run. If you would rather keep your login, add
`--login`:

```bash
isolate run --agent claude --login
```

What this does, plainly: the sandbox normally gives the agent a fresh, empty home
each run, so the agent cannot see its saved login. `--login` fixes that in two
steps. First, it shares the agent's own config folder from your real home, as a
writable bind. Second (the important part), it tells the agent to look there by
setting the agent's config-dir variable inside the sandbox: `CLAUDE_CONFIG_DIR`
for Claude, `GEMINI_DIR` for Gemini. Without that variable the agent would still
look inside the throwaway home and miss the login, which is why simply granting
the folder is not enough on its own.

Expect to sign in once. Many agents keep their real login in the operating
system keychain, which the sandbox deliberately does not expose (that is part of
keeping your secrets out). So the first `--login` run inside the sandbox may still
ask you to sign in. That one sign-in is then saved as a file in the shared config
folder, and every later run reuses it, even in other projects, with no prompt.

The trade-off is that the sandboxed agent can now read and change that one config
folder in your real home, which is a little more access than the strict default.
It is your own agent's data, so this is usually fine, but it is opt-in on purpose
so the choice is yours.

### What if my agent is not "known"?

Only `claude` and `gemini` are built in today. For anything else, grant the paths
by hand with `--allow-read` (and run it by its full path), or ask for it to be
added as a known agent. Use `--dry-run` to see exactly what is shared.

## Where settings come from (the layer cake)

isolate decides the final settings by stacking layers. Each higher layer can
change what a lower one set. From bottom to top:

1. **Built-in defaults** (baked into the tool).
2. **Your global file**: `~/.config/isolate/config.yml`.
3. **The project file**: `./.isolate.yml` in the current folder.
4. **The flags you type** on the command line.

So a flag always wins over a file, and the project file wins over your global
file. This is like getting dressed: the coat (the flag you typed now) goes on top
of the shirt (the project file) which is on top of the vest (your global file).

For list settings (`writable`, `readable`), the files **replace** the list, but
the command-line `--allow-write` / `--allow-read` flags **add** to it. That way
typing `--allow-write /data` widens access instead of throwing away the project
folder you already had.

## A starter config file

See [examples/.isolate.yml](../examples/.isolate.yml). Copy it to your project as
`.isolate.yml` and edit it. Anything you leave out keeps the built-in default.

## Worked examples

```bash
# The everyday case: run an agent on the current project.
cd ~/Projects/my-app
isolate run -- claude

# Read-only review: let the agent look but not change or phone home.
isolate run --profile readonly -- claude

# Air-gapped test run with a tighter memory cap.
isolate run --no-network --memory 2G -- pytest

# Let the agent also write to a shared library folder next door.
isolate run --allow-write ~/Projects/shared-lib -- claude

# Learn what is happening: print the exact sandbox command, run nothing.
isolate run --dry-run -- claude
```

## Understanding `--dry-run` output

`--dry-run` prints the real command isolate would run. It usually starts with
`systemd-run ... --` (the part that sets CPU and memory limits) followed by
`bwrap ... -- <your command>` (the part that builds the room). Reading it once is
the fastest way to understand exactly what the bubble allows. Each flag is
explained in the [bubblewrap primer](primers/bubblewrap.md).

## When something the agent needs is missing

Because the bubble starts empty and we only add what we list, sometimes a program
fails because we did not hand it a folder it wanted. This is safe (it fails, it
does not leak), but it can be confusing. The fix is usually to grant the missing
path with `--allow-read` or `--allow-write`. Use `--dry-run` to see what is and is
not being shared.
