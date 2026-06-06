# Primer: Linux namespaces (private views of the system)

Namespaces are the walls of our playpen. This primer explains what they are with
everyday pictures. No prior knowledge needed.

## The one-sentence idea

A namespace gives a program its **own private version** of some part of the
system, so what it sees is not the real shared thing, but a separate copy that
only affects it.

## The hotel analogy

Picture a big hotel. There is one real street address, but every room has its own
"Room 1" written on its own door, its own little fridge, its own phone. When a
guest in one room picks up "the phone", they get their room's phone, not the whole
hotel's switchboard. Each room has a private version of things that, from inside,
feels like the only one.

A namespace does this for parts of Linux. Linux has several kinds, and you can
give a program a fresh, private copy of each.

## The kinds that matter for a sandbox

### Mount namespace (private view of files)

This is the big one. Normally every program sees the same single tree of folders
(`/home`, `/etc`, `/usr`, and so on). A **mount namespace** lets us build a
**different** tree just for the sandboxed program.

We start it with an empty tree and then place only what we choose into it: the
system libraries (read-only), and your one project folder (writable). Your real
home folder is simply never placed inside, so it does not exist in that program's
world. It is like handing the guest a map of the hotel that only shows their own
room and the lobby. They cannot walk to a room that is not on their map.

### PID namespace (private list of processes)

Every running program has a number (a PID) and can normally see all the other
running programs. A **PID namespace** gives the sandboxed program its own fresh
list, starting over. It cannot see, inspect, or interfere with your other
programs, because in its world they do not appear at all. Like a guest who can
only see the people inside their own room.

### Network namespace (private network)

A **network namespace** gives the program its own network stack. We can give it
one with no connection to the outside (air-gapped), or share the real one when the
agent needs the internet. With no sharing, the only "network" inside is a
loopback that talks to itself, like a phone that can only call itself.

### User namespace (private identities, no root needed)

This is the clever one that makes everything work **without administrator
rights**. A **user namespace** lets a normal user be "root" **inside** the
sandbox only, while still being just a normal, powerless user **outside**. It is
like being made "captain" of a toy boat: full authority on the toy boat, zero
authority over the real navy. This is why `isolate` never needs `sudo` to build
the bubble.

### Plus a few more

bubblewrap can also give fresh **IPC** (a private channel for programs to talk),
**UTS** (a private hostname), and **cgroup** views. `isolate` asks bubblewrap to
isolate all of them at once with a single flag.

## How isolate uses them

When you run `isolate`, it tells bubblewrap (via the flag `--unshare-all`):
"create new, private versions of all these namespaces for this program". Then it
selectively shares back only what is needed (the network, if you allowed it). The
result is a program living in its own small world, built from your real one but
showing only the parts you chose.

You can see this yourself by running `isolate run --dry-run -- <cmd>` and looking
for `--unshare-all` and `--share-net` in the printed command. The
[bubblewrap primer](bubblewrap.md) explains each flag.

## Why this is safe by construction

Because the program's world is built by **adding** chosen things to an empty
space, anything you forget to add is just absent. There is no "oops, I left the
door to my home folder open", because the door was never installed. Safety is the
default, and access is the exception. That is the whole philosophy.
