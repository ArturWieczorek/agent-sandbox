# agent-sandbox - a simple safety bubble for AI agents

> The project is called **agent-sandbox**. The command you actually type is
> **`isolate`** (short and easy). Same tool, two names: one is the repo, one is
> the command, much like the project "ripgrep" ships the `rg` command.

## What is this, in one sentence?

`isolate` lets you run an AI agent (like Claude or Gemini) or any command inside
a safe "bubble", so it can freely work on one project folder but cannot see your
secrets or damage the rest of your computer.

## The problem, explained with a real life picture

Imagine you hire a very fast, very eager helper to tidy one room in your house.
Most of the time they do great work. But this helper is not careful: now and
then they wander into other rooms, open drawers, and sometimes throw the wrong
things in the bin. You cannot watch them every second.

An AI agent running on your computer is exactly like that helper. It is powerful
and useful, but if you let it run "loose" on your normal account, it can touch
**everything you can touch**: your SSH keys, your saved passwords, your other
projects, your whole home folder. One careless command and something important
is gone.

`isolate` is the solution: it puts the helper in **one room with a locked door**.
We hand them only that room and the tools they need. The key in their pocket does
not open any other door. When they are done, we throw the room key away.

## How it keeps you safe (the four walls of the bubble)

1. **It hides your files.** Your real home folder is never put inside the bubble.
   So the agent simply cannot see `~/.ssh`, `~/.aws`, or your other projects.
   They do not exist as far as the bubble is concerned.
2. **It allows writing in only one place.** The agent can create and change files
   in the one project folder you point it at, and nowhere else on the real disk.
3. **It can cut off the internet.** With one flag (`--no-network`) the bubble is
   fully air-gapped. By default network stays on, because most agents need it to
   talk to their own service.
4. **It caps how much it can use.** Using a built-in Linux feature, we put a limit
   on how much memory and CPU the agent can take, so a runaway agent cannot freeze
   your machine.

## The engine under the hood

`isolate` is a thin, friendly wrapper around two standard Linux tools:

- **bubblewrap** (`bwrap`): builds the room and its locked door. It is the same
  trusted sandbox technology that Claude Code itself uses on Linux.
- **systemd** (a "scope"): the part that sets the food limits (CPU and memory).

We did not invent a new way to be safe. We took the tools the experts already use
and made them easy to run for everyday work. If you want to understand the ideas
behind them, the [primers](docs/primers/) explain everything from scratch, in the
same plain language as this page.

## Install

You need Linux, Python 3.11 or newer, and the `bubblewrap` package.

```bash
# 1. Install bubblewrap (Ubuntu/Debian example).
sudo apt install bubblewrap

# 2. Get the code and install it (this gives you the `isolate` command).
git clone https://github.com/ArturWieczorek/agent-sandbox.git
cd agent-sandbox
pip install .

# 3. Check your machine has everything (this never changes anything).
isolate doctor
```

`isolate doctor` is like the lights on a car dashboard before a drive: it tells
you, in plain words, if anything is missing and the exact command to fix it.

## Use it

```bash
# Go into the project you want the agent to work on.
cd ~/Projects/my-app

# Run the agent inside the bubble. Everything after -- is the command to run.
isolate run -- claude

# Run with no internet at all (fully air-gapped).
isolate run --no-network -- claude

# See exactly what would run, without running it (great for learning).
isolate run --dry-run -- claude

# Give the agent extra room: more memory, a second writable folder.
isolate run --memory 8G --allow-write ~/Projects/shared-lib -- claude
```

The word `--` (two dashes on their own) is the fence: everything to the **left**
configures the bubble; everything to the **right** is the command that runs
inside it.

Full options and examples are in [docs/usage.md](docs/usage.md).

## Important: what this does and does not protect against

Please read [docs/security-model.md](docs/security-model.md). The short version,
told honestly:

- This is a **strong, real** safety bubble for the everyday risk: an agent making
  a mess, deleting the wrong files, or reading your secrets by accident.
- It is **not** a bank vault against a determined human attacker who has a brand
  new, unknown Linux kernel bug. That is true of all tools in this family
  (including Docker). For that higher level of safety you need a full virtual
  machine (the doc explains the options).

## Learn the concepts from zero

If words like "namespace" or "cgroup" are new to you, start here. Each primer
assumes you know nothing and builds up with everyday analogies:

- [What isolation means](docs/primers/isolation-basics.md)
- [Namespaces (separate views of the system)](docs/primers/namespaces.md)
- [cgroups (limits on CPU and memory)](docs/primers/cgroups.md)
- [Bubblewrap (the sandbox engine)](docs/primers/bubblewrap.md)
- [seccomp (filtering dangerous commands)](docs/primers/seccomp.md)

## For people working on this project

- [docs/architecture.md](docs/architecture.md): a detailed, plain-language tour of
  how the code is built (what each file does, where, and why).
- [AGENTS.md](AGENTS.md): the engineering rules we follow (test-first development,
  the safety model, and how we write docs).

## Develop and test

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Fast tests (no real sandbox launched):
pytest -m "not integration"

# Everything, including real bubblewrap runs:
pytest
```

## License

Released under the MIT License. In plain words: you may freely use, copy, change,
and share this code, including for commercial use, as long as you keep the
copyright notice. It comes with no warranty. See the [LICENSE](LICENSE) file for
the full text.
