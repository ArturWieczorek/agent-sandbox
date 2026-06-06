# Project CLAUDE.md (isolation-container)

These are hard rules for this repo. They override default behavior. Follow them
exactly, in code, in docs, and in everything you write to the user.

## Rule 1: Never use em dashes or en dashes

Do NOT use the em dash character (Unicode U+2014, the long dash) or the en dash
character (Unicode U+2013, the medium dash) anywhere. This applies to:

- Code (comments, strings, identifiers, anything).
- Documents and README files.
- Every message and response you send to the user.

Always use a plain regular hyphen ("-", the normal keyboard minus key) instead.

Think of it like this: imagine you only own one kind of pen, a short one. Even
if a fancier longer pen exists, you never reach for it. You write every dash
with the one short pen you have. That short pen is the regular hyphen.

The only exception: if a tool, a special condition, a fixed format, or some
outside situation forces an em dash or en dash (for example a code formatter
that rewrites text automatically, or pasted output you must keep exact), then
and ONLY then it is allowed. In plain words: you never type one on purpose, but
if a machine puts one there for reasons you cannot control, that is fine.

## Rule 2: Never author commits, comments, or anything

Do NOT add yourself (Claude) as the author or co-author of anything.

- In git commits: do NOT add a "Co-Authored-By: Claude" line, and do NOT add a
  "Generated with Claude Code" line or any similar credit. The commit should
  look like the user wrote it, with no sign of an AI helper.
- In code comments and any other text: do NOT sign your name, do NOT add
  "written by Claude" notes, and do NOT leave any mark that says an AI made it.

Real life picture: you are a ghostwriter. You help write the letter, but your
name never appears on it. The letter looks like the user wrote every word.

## Rule 3: Always explain in VERY simple language, with detail and analogies

When you write any document, any README, or any message to the user, you must:

- Be VERY detailed. Do not skip steps. Spell things out fully.
- Use VERY simple language. Short words. Short sentences. Imagine you are
  explaining to a smart person who is brand new to the topic.
- Use analogies, and real life examples when you can. Compare hard ideas to
  everyday things like cooking, mailing letters, locked doors, or traffic, so
  the idea becomes easy to picture.

The goal: a reader with no background should finish reading and fully
understand, because every idea was broken down and tied to something familiar.
