# Agent Skills

A collection of reusable agent skills designed to extend AI coding assistants with specialized, on-demand knowledge and workflows.

## What is a skill?

A skill is a focused bundle of instructions, references, and resources that an agent loads when a task matches a specific domain. Skills bias an agent toward accurate, up-to-date practices for a particular area of work — for example, a framework, a platform, a tooling ecosystem, or a repeatable workflow.

Each skill is self-contained and follows a consistent contract so it can be discovered, loaded, and executed predictably by any compatible agent runtime.

## Install

Install skills with the [`skills`](https://github.com/vercel-labs/skills) CLI:

```sh
npx skills add dbrkv/skills
```

Install a specific skill, or to a specific agent:

```sh
npx skills add dbrkv/skills --skill code-security-review
npx skills add dbrkv/skills -a claude-code -a kilo
```

## Why skills?

- **Precision over recall.** Instead of relying solely on pretrained knowledge, skills inject curated, authoritative context for a narrow domain.
- **Consistency.** Encoded workflows ensure the agent follows the same proven steps every time.
- **Portability.** A well-formed skill can be shared, versioned, and reused across projects and teams.
- **Extensibility.** New capabilities can be added without modifying the core agent — just drop in a new skill.

## Contributing

Contributions are welcome. A good skill:

- Has a clear, specific trigger description so it activates only when relevant.
- Biases toward retrieval from authoritative sources (official docs, specs) over pretrained knowledge.
- Is scoped tightly — one coherent capability per skill.
- Includes examples, references, and any scripts or templates needed to execute the workflow.
- Follows the project's naming and layout conventions.

## License

See the repository for license details.
