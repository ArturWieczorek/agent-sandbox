# Primer: what "isolation" actually means

New to the whole idea of a sandbox? Start here. This assumes you know nothing and
builds up slowly with everyday pictures.

## The core idea

"Isolation" means running a program in a way where it can only see and touch a
small, chosen part of your computer, instead of all of it.

Real life picture: think of a **child's playpen**. The child can play freely with
everything inside the pen. But they cannot reach the stairs, the stove, or the
power sockets, because a barrier stands between them and the rest of the room. The
playpen does not make the child less able to play; it just limits where the
playing can happen. A sandbox is a playpen for a program.

## Why we need it for AI agents

An AI agent is a program that decides its own next action and then does it,
quickly, many times in a row. That is wonderful for getting work done and risky
when it is wrong. Without a playpen, "wrong" can mean a deleted folder or a leaked
password. With a playpen, "wrong" just means a harmless mistake inside the pen
that you throw away afterward.

## The two ways to build a barrier

There are two broad families of isolation, and they sit at opposite ends of a
see-saw between **speed** and **strength**.

### 1. Share the kernel (light and fast)

Your operating system has a core called the **kernel**. Think of it as the
building's shared plumbing and wiring: every program uses it to actually read
files, use the network, and so on.

In this family (which includes bubblewrap and Docker), every program still uses
the **same** kernel, but the kernel hands each program a **different view** of the
world: a different set of visible files, its own list of processes, maybe no
network. It is like an office building where everyone shares the same plumbing,
but each tenant has their own locked suite and cannot enter the others.

- Good: starts in milliseconds, uses almost no extra memory.
- Limit: because everyone shares the plumbing (the kernel), a flaw in the plumbing
  could, in rare cases, let someone leak into another suite.

`isolate` lives here, because for everyday work the speed is worth it and the risk
is small.

### 2. Do not share the kernel (heavy and strong)

In this family (virtual machines, gVisor, microVMs), the guest gets its **own**
kernel, or a fake stand-in kernel. It is like giving the tenant a completely
separate building with its own plumbing. Even a burst pipe in their building
cannot flood yours.

- Good: a break-in stays fully contained.
- Limit: slower to start and uses much more memory, because you are running a
  whole extra system.

## Where isolate sits, and why

`isolate` chooses the light-and-fast family (bubblewrap) on purpose, because the
common danger is an agent making a **mistake**, not a hacker launching a
**kernel exploit**. A fast, friendly playpen you actually use every day beats a
heavy vault you avoid because it is slow.

If your situation is the rarer, scarier one (truly untrusted code, a real
attacker), read the end of the [security model](../security-model.md) for the
heavier options.

## The pieces that make the playpen

A real sandbox is built from a few kernel features working together. Each has its
own primer:

- [Namespaces](namespaces.md): give the program its own private view of files,
  processes, and the network. These build the walls.
- [cgroups](cgroups.md): limit how much CPU and memory the program may use. This
  is the portion control.
- [seccomp](seccomp.md): block dangerous low-level commands the program might try.
  This is an extra filter on the door.
- [bubblewrap](bubblewrap.md): the tool that pulls all of the above together into
  one easy command, which is what `isolate` drives.
