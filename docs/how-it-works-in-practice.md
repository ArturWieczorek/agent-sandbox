# How it works in practice

This page answers the everyday question: if I stand in a project folder and run
this, what do I actually get, and how does it hold me back? It is the practical
companion to the [security model](security-model.md) (which covers the deeper
"what is and is not protected" question).

## The one-line picture

You type, from inside a project:

```bash
cd ~/Projects/VotingAnchor
isolate run --agent claude --login
```

The tool builds a sealed "room", drops the agent inside it, hands the agent
**only your VotingAnchor folder plus the bare tools it needs**, and runs it. When
the agent exits, the room is torn down. Your real work in the folder stays;
everything else about the room vanishes.

The analogy to keep in mind: it is a **workshop with one locked door**. The agent
can do anything to the project on the workbench, but the door to the rest of your
house does not open from the inside.

## What it gives you (the freedoms inside the room)

- **Full control of this one project.** The agent can read, create, edit, and
  delete files anywhere inside the current folder and its subfolders. These are
  your **real files**: the changes are permanent and are there after the agent
  exits. This is the whole point, real work gets done.
- **The normal tools.** The system programs and libraries (things under `/usr`,
  `/bin`, and so on) are present, read-only, so `python`, `git`, `node`,
  compilers, and the like all work as usual.
- **The internet (by default).** The agent can reach its own service, fetch
  packages, and call APIs. So `pip install`, `npm install`, and web requests work,
  as long as what they install lands inside the project.
- **A fresh, private scratch space.** It gets its own empty `/tmp` and its own
  throwaway home folder, so it can scribble temporary files without touching
  yours.
- **The agent itself, ready to use.** `--agent claude` quietly hands in the agent
  program and (with `--login`) your sign-in, so you just run it.

## How it limits the agent (the locked door)

This is the safety. Inside the room, the agent **cannot**:

- **See anything outside the project.** Your home folder, your other projects,
  your `~/.ssh` keys, your `~/.aws` credentials, your saved passwords: none of
  them exist as far as the room is concerned. They are not "blocked", they are
  simply not in the room.
- **Change the rest of your computer.** The system files are read-only, so a stray
  `rm -rf /usr` or a bad install just bounces off ("read-only file system"). If
  the agent writes to some other path it was not given, that write lands on a
  throwaway in-memory surface and disappears when it exits. Your real system is
  never altered.
- **Spy on or kill your other programs.** It gets its own fresh list of processes,
  so your browser, editor, and other work are invisible and untouchable.
- **Hog the machine.** There is a memory cap and a CPU cap (by default about 4 GB
  and 2 cores). A runaway process hits the ceiling and is stopped, instead of
  freezing your whole computer.
- **Phone home if you say so.** Add `--no-network` and the room is completely
  air-gapped: no internet at all.

## How it limits you (the everyday friction)

Honesty matters, so here are the rough edges you will actually feel:

- **"Deny by default" means occasional "not found".** Because nothing enters the
  room unless it was handed in, a tool that lives in your home (not in the system
  folders) will be missing. That is exactly why `--agent` exists, and why you
  sometimes add `--allow-read /some/path`. If something fails oddly, the usual fix
  is to grant the path it needs. Run with `--dry-run` to see precisely what is
  shared.
- **The bubble does not protect the project from itself.** The agent has a real
  key to this room, so if it deletes a file *inside* the project, that file is
  really gone. The bubble guards everything **outside** the folder, not the
  folder. Your safety net for the folder is **git**: commit before you let it
  loose, then `git diff` to review and `git checkout` to undo.
- **Things installed system-wide do not stick.** If the agent tries to install a
  system package or write to your home config, that vanishes with the room.
  Anything it installs into the project folder (a local `node_modules`, a Python
  virtual environment in the repo) does persist.
- **One-time sign-in.** With `--login`, the first run asks you to sign in once
  (your real login is in the operating system keychain, which the room
  deliberately cannot open). After that it persists across all projects. See the
  `--login` section in [usage.md](usage.md#the-login-trade-off---login).

## Quick reference

| Inside your project folder, the agent... | Result |
| --- | --- |
| Edits, creates, deletes project files | Real and permanent (use git to review/undo) |
| Reads system tools and libraries | Yes, read-only |
| Uses the internet | Yes by default; off with `--no-network` |
| Reads your home, other projects, SSH/cloud keys | No, invisible |
| Writes to system folders or outside the project | Blocked or thrown away; real system untouched |
| Uses unlimited CPU/memory | No, capped so it cannot freeze your machine |
| Sees your other running programs | No |

## The honest edge of the safety

This is a very strong everyday guard against an agent making a **mess** or
**reading your secrets** by accident. It is not a bank vault against a determined
attacker armed with a brand-new, unknown Linux kernel flaw (no lightweight
sandbox is, including Docker). For that rare, extreme case you would step up to a
full virtual machine. The full write-up of what it does and does not protect
against is in [security-model.md](security-model.md).

So in one sentence: **run it in a project and the agent works on that project for
real, with the internet and normal tools, but it cannot see your secrets, cannot
harm the rest of your system, and cannot run your machine into the ground.**
