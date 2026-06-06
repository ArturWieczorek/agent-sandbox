# Primer: seccomp (filtering the commands a program may use)

This is the most advanced of the primers, and the good news is you do not need it
to use `isolate` today. It explains an extra layer of safety that bubblewrap
supports and that we may add later. Read it to understand the full picture.

## First, what is a "system call"?

Every program, deep down, gets real work done by asking the kernel to do it.
"Open this file." "Send these bytes over the network." "Start a new process."
Each such request is called a **system call** (or "syscall"). There are a few
hundred of them. They are the only doorways through which a program can affect the
real world.

Real life picture: imagine a guest in our hotel room who can only interact with
the outside by filling in request slips and pushing them under the door: "bring
me a towel", "make a phone call", "open the safe". Every slip is a system call. The
staff (the kernel) reads the slip and acts on it.

## What seccomp does

**seccomp** (secure computing mode) is a filter that sits at the door and checks
each request slip before the staff sees it. You give it a list of rules, and it
can **allow**, **block**, or **error out** specific kinds of requests.

So even inside the room, you can say: "this guest is allowed to ask for towels and
phone calls, but any slip that says 'open the safe' or 'rewire the building' gets
torn up at the door." It is a second, finer filter, on top of the walls that
[namespaces](namespaces.md) already built.

## Why add it on top of namespaces?

Namespaces limit **what the program can reach**. seccomp limits **what kinds of
actions it can even request**. They cover different risks:

- Namespaces stop the program from seeing your files.
- seccomp can stop the program from using rare, dangerous, or exotic system calls
  that are common ingredients in attempts to break out of a sandbox by exploiting
  a kernel bug.

Blocking the unusual doorways shrinks the "attack surface": fewer doorways means
fewer possible weak spots. This is why high-security sandboxes almost always
combine both.

## How bubblewrap supports it

bubblewrap can load a compiled seccomp filter with its `--seccomp` flag. The
filter itself is a small program in a format called BPF (a tiny rule language the
kernel runs). Building a good filter is delicate: block too much and normal
programs break; block too little and you gain little safety.

## Why isolate does not enable it by default (yet)

Two honest reasons:

1. **Compatibility.** A wrong filter makes ordinary tools fail in confusing ways.
   Getting a filter that is safe for "any command an AI agent might run" is hard,
   and a broken default would frustrate everyday use.
2. **Diminishing returns for the common case.** Our main goal is stopping
   **accidents** (deleting files, leaking secrets), which the file and network
   walls already handle well. seccomp mainly hardens against a deliberate **kernel
   exploit**, which is the rarer, expert-level threat.

For that rarer threat, the bigger win is hardware-level isolation (a virtual
machine or gVisor), described at the end of the [security model](../security-model.md).
A seccomp profile is on the list of possible future additions for users who want
defense in depth without going all the way to a VM.

## The takeaway

- A system call is a program's request slip to the kernel.
- seccomp is a filter at the door that can tear up dangerous slips.
- It is a powerful **extra** layer, not a replacement for the walls.
- `isolate` leaves it off for now to keep everyday use smooth and honest about
  what actually helps most.
