# Primer: bubblewrap (the sandbox engine isolate drives)

`isolate` does not do the low-level safety work itself. It hands that to a small,
trusted tool called **bubblewrap** (the command is `bwrap`). This primer explains
what bubblewrap is and what each flag we use actually does, in plain words.

## What bubblewrap is

bubblewrap is a tiny program whose only job is to build a sandbox using the Linux
[namespaces](namespaces.md) and run one command inside it. It is unprivileged (no
`sudo` needed), has no background service, and is fast. It is the same tool that
Flatpak uses to sandbox desktop apps, and that Claude Code uses on Linux. In other
words, it is well-tested and widely trusted.

The key idea: bubblewrap starts the sandbox as an **empty room** (a fresh
in-memory filesystem) and you tell it, piece by piece, what to put in. Nothing is
shared unless you ask for it.

## The flags isolate uses, explained

Run `isolate run --dry-run -- <cmd>` to see the real command. Here is what each
part means. Read it like a recipe: each line adds one thing to the empty room.

### Putting files in the room

- `--ro-bind SRC DEST`: place the host folder/file `SRC` into the room at `DEST`,
  **read-only**. We use this for system libraries (`/usr`) and a few `/etc` files
  the program needs to start. Read-only means the program can use them but never
  change them.
- `--bind SRC DEST`: same, but **read-write**. We use this only for your project
  folder and the throwaway fake home. These are the only real places the program
  can change.
- `--ro-bind-try SRC DEST`: like `--ro-bind`, but if `SRC` does not exist, skip it
  quietly instead of failing. Handy for optional files.
- `--symlink TARGET LINK`: create a symbolic link inside the room. Modern Linux
  makes `/bin`, `/lib`, etc. into links pointing into `/usr`. We recreate those
  same links so programs find things where they expect, without mounting the same
  folder twice.
- `--proc /proc` and `--dev /dev`: give the room a fresh, safe `/proc` (process
  info) and `/dev` (devices) that every normal program expects.
- `--tmpfs /tmp`: give the room its own private, in-memory `/tmp` scratch space
  that disappears when the room closes.

### Building the walls

- `--unshare-all`: create fresh, private versions of all the
  [namespaces](namespaces.md) at once: files, processes, network, hostname, and
  more. This is the main "build the walls" flag.
- `--share-net`: poke one hole in the wall for the network, so the agent can reach
  its service. `isolate` adds this only when network is allowed; `--no-network`
  leaves it out, giving a fully air-gapped room.
- `--chdir DIR`: start the program inside `DIR` (your project folder).

### Safety extras

- `--die-with-parent`: if the launcher goes away, the sandbox dies too. No
  forgotten programs left running in a leftover room.
- `--new-session`: start a brand-new terminal session. This blocks an old trick
  (called TIOCSTI) where a program fakes keystrokes into your terminal.
- `--clearenv`: wipe **all** inherited environment variables, then we set back
  only a small, safe few (`HOME`, `PATH`, `TERM`). This stops secrets that live in
  environment variables (like API tokens) from leaking into the sandbox by
  accident.
- `--setenv NAME VALUE`: set one environment variable inside the room. We point
  `HOME` at the throwaway fake home, so the program never looks in your real one.

### The fence

- `--` (two dashes alone): tells bubblewrap "I am done giving you options; the
  rest is the program to run". Everything after it is your command.

## Why we trust it

bubblewrap is small on purpose. A small tool is easy to audit and hard to get
wrong. It does one job (build a namespace sandbox and run a command), it needs no
special privileges, and it is used by millions of desktops through Flatpak. We
build on that foundation rather than inventing our own.

## What bubblewrap does NOT do

bubblewrap builds the walls (what you can see and touch). It does **not** limit how
much CPU or memory the program uses; that is the job of [cgroups](cgroups.md),
which `isolate` adds separately through systemd. Knowing this split (walls from
bubblewrap, portion control from cgroups) is the key to understanding how the
whole tool fits together.
