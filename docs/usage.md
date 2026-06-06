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
| `--profile NAME` | Use a named bundle of settings. Default is `default`. |
| `--no-network` | Cut off the internet completely (air-gapped). |
| `--network` | Force the internet on (this is already the default). |
| `--memory SIZE` | Memory cap, like `4G` or `512M`. The program cannot exceed it. |
| `--cpus N` | CPU cap in cores, like `2` or `0.5` (half a core). |
| `--allow-write PATH` | Let the bubble also write to PATH. Repeatable. |
| `--allow-read PATH` | Let the bubble also read PATH (read-only). Repeatable. |
| `--home PATH` | Use PATH as the throwaway fake home. |
| `--config FILE` | Read one more config file, layered on top of the rest. |
| `--dry-run` | Print the command that would run, but do not run it. |

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
