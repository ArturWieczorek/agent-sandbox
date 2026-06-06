# Security model: what isolate protects against (and what it does not)

This page is deliberately honest. A safety tool that oversells itself is
dangerous, because you trust it for things it cannot do. So here is the plain
truth about where the bubble is strong and where it is not.

## The mental model: a hotel room, not a bank vault

A good hotel room keeps an ordinary guest where they belong. The door locks, the
key only opens that one room, and the guest cannot wander into the manager's
office. For normal guests, this is excellent protection.

But a hotel room is not a bank vault. A determined professional thief with
special tools and inside knowledge might still get past a hotel lock. If you are
defending against that level of threat, you need a vault, not a room.

`isolate` builds you a very good hotel room. For most real risks that is exactly
the right tool. For the rare, extreme threat, you need the vault (a full virtual
machine), which we point to at the bottom.

## What it protects against (the strong part)

These are the everyday dangers, and the bubble handles them well:

- **Accidental damage.** The agent runs a wrong command (`rm -rf` in the wrong
  place, a bad build script). Because only the project folder is writable on the
  real disk, the rest of your system cannot be changed or deleted.
- **Reading your secrets.** Your real home folder is never mounted into the
  bubble. So `~/.ssh`, `~/.aws`, `~/.gnupg`, saved tokens, and your other
  projects are simply not there to be read or copied.
- **Unwanted "phone home".** With `--no-network`, the agent has no internet at
  all, so it cannot send your code or data anywhere.
- **Resource hogging.** CPU and memory caps stop a runaway agent from freezing
  your whole machine.
- **Some process tricks.** A fresh process namespace hides your other running
  programs, and a new terminal session blocks a classic keystroke-injection
  trick (TIOCSTI).

## How the protection is built (the honest mechanics)

The bubble starts as an **empty room** (a fresh in-memory filesystem). Nothing
from your computer is inside it unless we explicitly hand it over. We then add,
read-only, just the system libraries and a few harmless config files the program
needs to start, plus your one project folder (this one read-write). This is a
**whitelist**: "deny everything, then allow a named few". Forgetting to allow
something makes the program fail safely; it never accidentally leaks.

A subtle but important point: if the agent writes to a path we did **not** share
(say `/etc/something`), that write lands on the throwaway in-memory room and
vanishes when the bubble closes. It never reaches the real file. So even "writing
outside the project" does not harm your real system.

## What it does NOT protect against (the limits)

Be clear-eyed about these:

- **A kernel escape.** The bubble shares the one Linux kernel with your real
  system (this is how all lightweight sandboxes work, Docker included). If an
  attacker has a brand new, unpatched kernel bug, they could in theory break out.
  This is rare and hard, but not impossible.
- **Anything you explicitly grant.** If you run `--allow-write ~` or hand it your
  `.ssh` folder, the bubble will do as told. isolate prints a warning when it
  spots a known-dangerous grant, but it obeys you. Least privilege is your job:
  grant the minimum.
- **Network-based mischief when the network is on.** By default the network is
  shared so the agent can reach its service. While on, the agent can talk to the
  internet like any program. Use `--no-network` when you do not need it.
- **Things outside the bubble.** isolate protects the system from the command
  inside it. It does not protect the command from a hostile system, and it is not
  antivirus.

## When you need more than a hotel room

If your threat is a determined human adversary, or you are running truly
untrusted code that may carry kernel exploits, step up to **hardware-level
isolation**, where the guest does not share your kernel at all:

- **A virtual machine** (for example QEMU/KVM): a whole separate computer in
  software. Strongest, heaviest.
- **gVisor**: a thin "pretend kernel" in user space that intercepts the program's
  system calls, so the real kernel is shielded.
- **Firecracker / Kata Containers (microVMs)**: tiny fast virtual machines built
  for exactly this.

These cost more time and resources, which is why they are not the default. The
[isolation basics primer](primers/isolation-basics.md) explains the trade-off
between "light and fast" and "heavy and bulletproof".

## The one rule to remember

Grant the least you can. The safest bubble is the one that shares the fewest
things. Start with `--no-network` and only the project folder, and open up more
only when you actually need it.
