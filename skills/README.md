# Skills

Agent skills for this project, organized by lifecycle stage.

## Stages

Each skill lives in one of three directories:

| Directory    | Meaning                                                                                 |
| ------------ | --------------------------------------------------------------------------------------- |
| `incubator/` | Being drafted or actively iterated. Not ready for general use; shape may still change.  |
| `active/`    | Stable and ready to use. Maintained and expected to trigger correctly.                  |
| `archived/`  | Deprecated, superseded, or no longer maintained. Kept for reference, not for use.       |

### Transitioning

- **Incubating → Active** — move the skill once it has a tight trigger description, complete references and scripts, and has been exercised on a real task.
- **Active → Archived** — move rather than delete; note any successor in the skill's `SKILL.md`.
- **Incubating → Archived** — if a draft is abandoned before becoming active, archive it with a short reason.

## Skills

- **codebase-wiki** (`incubator/`) — build and maintain a codebase wiki: interconnected markdown pages explaining what the code does and how it fits together. Based on the [Factory `droid-evolved` wiki skill](https://github.com/Factory-AI/factory-plugins/tree/master/plugins/droid-evolved/skills/wiki).
- **code-security-review** (`incubator/`) — security review by source-level reasoning: recon and a STRIDE threat model, invariant-driven scouts over surface × trust-boundary units, a coverage critic, root-cause dedup, refute-first isolated verifiers (a second blind verifier for consequential verdicts), and run snapshots under `~/security-audit/` validated by script. Quick, full, and recheck modes; subagent, workflow, or linear execution. Attribution in its `NOTICE.md`.
