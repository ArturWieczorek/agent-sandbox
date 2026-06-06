# Primer: cgroups (limits on CPU, memory, and more)

Namespaces decide **what a program can see**. cgroups decide **how much it can
use**. This primer explains cgroups from scratch with everyday pictures.

## The one-sentence idea

A "cgroup" (short for "control group") is a way to put one or more programs into a
box and tell the kernel: "this box may use at most this much CPU, this much
memory, this many processes", and the kernel enforces it.

## The buffet analogy

Imagine an all-you-can-eat buffet. Without any rule, one very hungry guest could
pile their plate so high that there is no food left for anyone else, and the
kitchen cannot keep up. Chaos.

Now imagine the restaurant gives each guest a **tray of a fixed size** and says
"you may take as much as fits on your tray, and no more". Everyone still eats
well, but no single guest can starve the others or overwhelm the kitchen.

A cgroup is that tray. The food is your computer's CPU time and memory. The guest
is the program. The tray size is the limit you set.

## Why an AI agent needs a tray

An AI agent can accidentally start a process that uses all your memory (for
example a runaway build, or loading a giant file). Without a limit, your whole
computer can freeze: the mouse stops, other apps die, and you may have to force a
restart and lose work.

With a memory cap, the kernel steps in the moment the agent's box reaches the
limit. The agent's own process is stopped, but the rest of your machine keeps
running smoothly. The mess stays on the agent's tray.

## The two limits isolate sets

- **Memory cap** (`--memory`, e.g. `4G`): the most memory the bubble may use. Hit
  the ceiling, and the kernel stops the offending process inside, not your system.
- **CPU cap** (`--cpus`, e.g. `2`): how much processor power the bubble may use,
  measured in cores. `2` means "up to two full cores' worth"; `0.5` means "half a
  core". Other programs keep their fair share.

`isolate` also sets a quiet limit on the number of processes (a guard against a
"fork bomb", which is a program that copies itself endlessly to clog the system).

## How isolate applies the tray: a systemd "scope"

You do not have to touch cgroups by hand. `isolate` asks **systemd** (the standard
manager for services on modern Linux) to create a temporary box called a
**scope**, set the limits on it, and run the whole sandbox inside it. The command
looks like this (you can see it with `--dry-run`):

```
systemd-run --user --scope -p MemoryMax=4G -p CPUQuota=200% -p TasksMax=512 -- bwrap ...
```

In plain words: "systemd, make me a temporary box for my own user, put a 4 GB
memory ceiling, a two-core CPU ceiling, and a 512-process ceiling on it, then run
this sandbox inside." `CPUQuota=200%` is just systemd's way of writing "two
cores", because 100% means one core.

## What if systemd is not available?

Some systems do not have a systemd user session. In that case `isolate` cannot set
the tray, so it tells you clearly and runs the sandbox **without** CPU/memory
limits. Everything else (the file and network walls) still works. The food limit
is the one feature that needs systemd; the walls do not.

## The bigger picture

cgroups are one of the two pillars of all container technology (the other being
[namespaces](namespaces.md)). Docker, Kubernetes, and systemd services all rely on
them. By using them here, `isolate` follows the same proven path the whole
industry uses, just packaged for simple daily use.
