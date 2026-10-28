# skills

Personal, opinionated agent skills. Experimental.

These are skills I build for my own work and run on my own projects. They
encode how I want an agent to do a job, not a neutral best practice, and
they change as I learn what works. Everything is in the **incubator**:
no stability promise, formats and behavior may change between commits. If
you use one, pin a commit.

## Skills

| Skill | What it does |
|-------|--------------|
| [code-security-review](skills/incubator/code-security-review/) | Security review of code by reading the source: a STRIDE threat model kept in the repository (`docs/security/threat-model.md`), a scan of the requested code across the six STRIDE categories, and an isolated refute-first validator for every finding. Diff review answers in chat; a full audit writes a dated report next to the threat model. The target is never executed. |
| [codebase-wiki](skills/incubator/codebase-wiki/) | Reads a repository and writes a `wiki/` of interconnected markdown pages explaining what the code does and how it fits together. |

## Opinions

What these skills assume, on purpose:

- **Verify before claiming.** A finding, a fact, or a "done" is backed by
  something checkable: a source trace, a script's output, a validator's OK.
- **Deterministic work goes to scripts.** IDs, storage paths, schema checks,
  and counting live in small stdlib-only scripts, not in the model's memory.
- **Leave the target alone.** A skill does not write artifacts into the
  repository it works on unless that output is the point (like a wiki).
- **Harness-neutral.** Written for any agent that loads skills (Claude Code,
  ZCode, Kilo, ...). Harness features such as subagents or workflows are used
  when present, with a stated fallback when not.
- **Not a replacement for CI.** Scanners, linters, and dependency checks
  belong in CI; skills cover what needs reasoning.

## Install

With the [`skills`](https://github.com/vercel-labs/skills) CLI:

```sh
npx skills add dbrkv/skills                              # all skills
npx skills add dbrkv/skills --skill code-security-review # one skill
npx skills add dbrkv/skills -a claude-code -a kilo       # specific agents
```

## Layout

```
skills/
  incubator/   drafts and skills under active iteration (everything, for now)
  active/      stable: tight trigger, exercised on real tasks
  archived/    retired, kept for reference
evals/         eval prompts, fixtures, and script tests per skill —
               kept outside the skill folders so they are not installed
```

Lifecycle rules are in [skills/README.md](skills/README.md).

## Credits

Some skills adapt material from other open-source skills; each such skill
carries a `NOTICE.md` with the source and its license.

## License

No license has been chosen for this repository yet. Third-party material
keeps its own license, stated in the skill's `NOTICE.md`.
