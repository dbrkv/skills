# Page structure specification

This reference defines the complete page layout for a generated wiki: what pages always exist, what sections are optional, how they are ordered and named, and what content each special page type should contain. Read this during the planning phase and when delegating page assignments to sub-agents.

## Contents

- [Always-present pages](#always-present-pages)
- [By the numbers](#by-the-numbers)
- [Lore](#lore)
- [Organizational lenses](#organizational-lenses)
- [Conditional sections](#conditional-sections)
- [How to monitor](#how-to-monitor)
- [Cleanup opportunities](#cleanup-opportunities)
- [Fun facts](#fun-facts)
- [Maintainers](#maintainers)
- [Per-page active contributors](#per-page-active-contributors)
- [Page ordering](#page-ordering)
- [Nesting rules](#nesting-rules)
- [Naming rules](#naming-rules)
- [Page title rules](#page-title-rules)
- [File structure tree](#file-structure-tree)
- [Meta file (`.wiki-meta.json`)](#meta-file-wiki-metajson)

## Always-present pages

These pages appear in every wiki, in this order:

1. `index.md` — wiki-root landing page. Its level-1 heading is the project name (e.g., "Acme platform"); the same heading is used as the site title by static site generators. The body is a one-to-two sentence summary of the project followed by links to the main sections (`overview/`, `how-to-contribute/`, and whichever lens sections the wiki has). This file is required: it is the only file that serves the root route (`/`), so without it every static site generator (VitePress, MkDocs, Hugo, Docusaurus, GitHub Pages) returns a 404 on first load.
2. `overview/` — introductory material grouped under one section
   - `index.md` — project overview: what it does, who uses it, quick links
   - `architecture.md` — system architecture with Mermaid diagrams
   - `getting-started.md` — prerequisites, install, build, test, run
   - `glossary.md` — project-specific terms and domain vocabulary
3. `by-the-numbers.md` — codebase statistics snapshot (see [By the numbers](#by-the-numbers))
4. `lore.md` — timeline and history of the codebase (see [Lore](#lore))
5. `how-to-contribute/` — how to work in this codebase
   - `index.md` — work pickup, PR process, review expectations, definition of done
   - `development-workflow.md` — branch, code, test, PR, merge cycle
   - `testing.md` — frameworks, patterns, how to run, mock, and cover
   - `debugging.md` — logs, common errors, troubleshooting runbook
   - `patterns-and-conventions.md` — error handling, coding style, cross-cutting concerns
   - `tooling.md` — build system, linters, code generators, CI tooling (if the repo's tooling is the product itself, promote this to a top-level section instead)

## By the numbers

A top-level `by-the-numbers.md` page that gives a quantitative snapshot of the codebase. Start the page with a "Data collected on [date]" note so readers know how current the numbers are.

Include these sections:

- **Size** — lines of code by language (with a Mermaid horizontal bar chart), total source files vs test files vs config files, package/module count for monorepos
- **Activity** — commits per week/month (recent trend), most actively changed files/directories in the last 90 days (churn hotspots)
- **Bot-attributed commits** — percentage of commits with bot co-authorship (e.g., `Co-authored-by: dependabot[bot]`, `github-actions[bot]`, `copilot[bot]`, or any `<name>[bot]` account). This is a lower bound on AI-assisted work since inline AI tools like Copilot leave no trace in git history. Be transparent about what's counted.
- **Complexity** — average file size by directory, deepest import chains, number of exported symbols per package

Use Mermaid `xychart-beta` (horizontal bar charts) for language breakdown and any other stat where a visual helps. Do NOT use Mermaid `pie` charts — they are not supported by the renderer. Use tables for lists of files/directories.

**Never include individual contributor stats** (top committers, lines per person, leaderboards). The by-the-numbers page is about the codebase, not the people. Per-person metrics create toxic comparisons and don't belong in team documentation. The `maintainers.md` page handles ownership mapping separately.

**Inline stats in other pages:** In addition to this summary page, weave relevant stats into existing pages:
- Language breakdown in `architecture.md`
- Churn hotspots in `cleanup-opportunities/` (if that section exists)
- File counts, bus factor (unique committers), and test-to-code ratio per subsystem on each domain page
- Dependency counts in `reference/dependencies.md`

## Lore

A top-level `lore.md` page that tells the story of how the codebase evolved. This is a narrative history, not a technical reference. It answers "what happened here and when?"

**Boundaries with other sections:**
- `by-the-numbers.md` = current snapshot (what the codebase looks like today)
- `lore.md` = timeline and history (what changed and when)
- `fun-facts.md` = light trivia (easter eggs, amusing discoveries)
- `background/` = technical rationale (why decisions were made)

**Every event, era, and milestone must include a date or month** (e.g., "Mar 2023", "Q4 2024"). Derive dates from git commit timestamps, tag dates, and file creation dates. If an exact date isn't available, use the month of the earliest relevant commit.

Include these sections:

- **Eras** — group the codebase history into 3-8 major phases, each with a short narrative description and key event bullet points. Derive from git history: tag dates, large merge commits, contributor patterns, directory creation dates. Example: "The TypeScript Migration (Mar–Aug 2023): The entire backend was rewritten from JavaScript to TypeScript over 5 months..."
- **Longest-standing features** — code or subsystems that have survived the most refactors and are still actively used. Include when they were first introduced and how many changes they've weathered.
- **Deprecated features** — things that were built, used, and then removed or replaced. Identify from directory names, README mentions, obvious `@deprecated` annotations, and removed routes. What was the feature, when was it introduced, when was it deprecated, and what replaced it.
- **Major rewrites** — large changes that touched many files. What existed before, what replaced it, and when. Derive from git history (large PRs, branch names with "migration" or "rewrite").
- **Growth trajectory** — how the codebase expanded over time: when packages/apps were added, contributor growth signals from git log.

**Speculation:** When the "why" behind a change isn't clear from commits, use natural hedging language ("appears to have been", "likely replaced due to"). No special formatting for speculative content.

## Organizational lenses

Five lenses are available for organizing the codebase deep-dives. Use any combination based on what the repo actually contains. At least one lens is required. Most repos use 2-3. The **features** lens is strongly encouraged -- it's the most intuitive entry point for new engineers ("what does this thing do?"). Even small repos typically have user-visible or developer-visible capabilities worth documenting. Only skip it if the repo is a single-purpose library with no distinct features.

| Concept | Default label | Also called | When to use |
|---|---|---|---|
| Deployable units | `applications/` | `services/`, `apps/` | Repo ships multiple distinct runtimes |
| Internal building blocks | `systems/` | `services/`, `modules/`, `subsystems/` | Architectural components that don't map to a single app or package |
| Cross-cutting capabilities | `features/` | `capabilities/`, `workflows/` | User-visible or developer-visible things that span multiple systems |
| Workspace packages | `packages/` | `libraries/`, `crates/`, `modules/` | Monorepo with shared libraries worth documenting individually |
| Foundational domain objects | `primitives/` | `core-concepts/`, `domain-models/`, `entities/` | Types/concepts that appear across 3+ systems (e.g., session, user, message) |

**Choosing labels:** Mirror the repo's own vocabulary. If the repo has an `apps/` directory, call the section `apps/`, not `applications/`. If the repo calls things "services," use `services/`. The default labels are fallbacks for when the repo has no existing convention.

**Placement rules:**
- Place each concept where the repo's structure suggests it belongs. If agent logic lives in `packages/agent-core`, document it under packages, not systems.
- The systems lens is for things that don't have a natural home in apps or packages -- emergent architectural patterns, cross-package systems, infrastructure that spans multiple directories.
- Do not duplicate content across lenses. If something is documented under packages, the relevant app page should cross-link to it, not repeat it.

**Heuristics for identifying each lens:**
- If it has its own entry point and deployment, it's an **application**
- If it's a workspace package that other packages import, it's a **package**
- If it's a module with internal logic and clear boundaries that doesn't map to a single package, it's a **system**
- If it's a type or concept that appears in 3+ systems, it's a **primitive**. Identifying primitives — and telling them apart from one-off types — takes more than directory spelunking: the model lives in fields, methods, events, and validation code spread across many files. Read `domain-model.md` before generating any `primitives/` page. It covers discovery signals (lexical, structural, behavioral, lifecycle, invariant, event), per-language probes, aggregate boundaries, ubiquitous language, a primitives-specific page template, and a worked example.
- If understanding it requires tracing through multiple systems or apps, it's a **feature**

## Conditional sections

Include these based on your judgment after surveying the repo. Skip any that don't apply.

- `api/` — if the repo exposes REST, GraphQL, WebSocket, or other APIs
- `deployment/` — if there's a non-trivial deployment process (CI/CD, environments, rollback, infrastructure)
- `security/` — if there are meaningful trust boundaries (auth, authorization, secrets, input validation)
- `background/` — if the repo has meaningful history (design decisions, pitfalls/danger zones, migration context)
- `how-to-monitor/` — if the repo runs as a service with logging, metrics, tracing, or alerting infrastructure
- `cleanup-opportunities/` — if the repo has dead code, accumulated TODOs/FIXMEs, oversized files, or outdated dependencies. Only include if there is actual content to report (see [Cleanup opportunities](#cleanup-opportunities))
- `fun-facts.md` — easter eggs, origin stories, oldest code, naming origins

## How to monitor

This conditional section documents how to see what the system is doing. Only generate it for repos that run as services with logging, metrics, or tracing infrastructure. Not applicable to libraries, CLI tools, or packages.

Sub-pages:

- `logging.md` — where logs go, how to query them, log levels and conventions, structured logging patterns, how to add new log statements
- `metrics.md` — what metrics are tracked, key SLIs/SLOs, available dashboards, how to add new metrics
- `tracing.md` — distributed tracing setup, how to trace a request end-to-end, span naming conventions, how to instrument new code paths
- `alerting.md` — what alerts exist, alert thresholds and rationale, escalation paths, known noisy alerts, how to add new alerts

Skip any sub-page the repo has no infrastructure for. If only one sub-page has content, collapse `how-to-monitor/` into a single `how-to-monitor.md` file instead of a directory.

## Cleanup opportunities

This conditional section surfaces actionable maintenance work. Only generate it if the scan finds meaningful content. Possible sub-pages:

- `dead-ends.md` — files, exports, or modules that nothing imports. The code equivalent of a ghost town.
- `todos-and-fixmes.md` — accumulated TODO, FIXME, and HACK comments with file locations. Include the oldest ones.
- `complexity-hotspots.md` — the largest source files, deepest nesting, or most complex functions. A gentle nudge toward refactoring.
- `dependency-freshness.md` — outdated or unmaintained dependencies. The oldest dependency still in use.

Skip any sub-page that has no findings. If only one sub-page has content, collapse `cleanup-opportunities/` into a single `cleanup-opportunities.md` file instead of a directory.

## Fun facts

The `fun-facts.md` page is optional but encouraged. Pick the 3-5 most interesting topics for the specific repo from this list:

- **Oldest surviving code** — find the oldest file or function via git blame. How old is it? Has it changed much?
- **Dependency archaeology** — the oldest dependency still in use, or the one with the most major version bumps
- **Naming origins** — why is the project or its internal tools named what they are? Engineers name things weirdly and there's usually a story
- **TODO/FIXME count** — how many TODO/FIXME/HACK comments exist? What's the oldest one?
- **The longest file** — which source file has the most lines? A gentle call-out that doubles as a refactoring hint

Do not force all of these into every wiki. Pick only the ones where the repo has something genuinely interesting to say. If nothing stands out, skip fun-facts entirely.

## Maintainers

Include a top-level `maintainers.md` page that maps subsystems to the people who know them. This page uses two data sources:

- **CODEOWNERS file** (if it exists) — official ownership assignments
- **Git blame / git log** — the 2-3 most recent or frequent committers per directory or subsystem

Present as a table:

```markdown
| Subsystem | Official owners (CODEOWNERS) | Recent contributors (git history) | Last activity |
|---|---|---|---|
| Authentication | @alice | alice, bob | 2 weeks ago |
| CLI | @charlie, @dave | charlie, eve | 3 days ago |
```

If the repo has no CODEOWNERS file, omit that column and derive all data from git history. If the repo has very few contributors (e.g., a solo project), skip this page entirely.

## Per-page active contributors

Each domain page (apps, systems, features, packages, primitives) should include an "Active contributors" byline as the very first line after the page heading, before the Purpose section:

```markdown
# Authentication

Active contributors: alice, bob

## Purpose
...
```

Derive the names from CODEOWNERS (if available) merged with the top 2-3 recent committers from git blame for that subsystem's directory. Use first names or GitHub usernames, no @ symbols.

**Exclude bot accounts** from contributor lists — filter out usernames ending in `[bot]` (e.g., `dependabot[bot]`, `github-actions[bot]`, `renovate[bot]`). Bots are not people you'd reach out to with questions. This applies to both the per-page active contributors byline and the maintainers page.

**Use the default branch for contributor data.** When deriving contributors from git blame or git log, always query against the default branch (`main` or `dev`), not the current branch. Feature branches skew contributor data toward whoever is working on that branch. Use `git log origin/main -- <path>` or `git log origin/dev -- <path>` to get accurate contributor history.

## Page ordering

The page ordering is critical for navigation. Every page must appear in its defined position — do NOT group childless pages together at the top or bottom.

The full ordering in the wiki is:

1. index.md (root landing page)
2. overview/ (index, architecture, getting-started, glossary)
3. by-the-numbers.md (if present)
4. lore.md (if present)
5. fun-facts.md (if present)
6. how-to-contribute/
7. [organizational lenses, in whatever order makes sense]
8. [conditional sections: api, deployment, security, how-to-monitor, background, cleanup-opportunities]
9. reference/
10. maintainers.md (if applicable, always last)

**Ordering rules:**

- The root `index.md` is always first. It is a landing page, not a section — do not list it in `topLevelSections`. Static site generators and the bundled VitePress adapter treat it as the homepage and exclude it from the sidebar (it is already reachable via the Home nav link).
- Each page stays in its defined position regardless of whether it has children. `by-the-numbers.md` appears after `overview/` even though it has no children, not at the top with other childless pages.
- The `pageOrder` array in `.wiki-meta.json` must exactly follow this ordering. It is the ordering hint provided to markdown viewers and static site generators.
- Within a lens section (e.g., `apps/`), order pages from most important to least important. The `index.md` is always first.
- Conditional sections appear in the order listed above (api → deployment → security → how-to-monitor → background → cleanup-opportunities), not alphabetically.

## Nesting rules

- Any page can expand into a directory with sub-pages, except the four pages inside `overview/` (`index.md`, `architecture.md`, `getting-started.md`, `glossary.md`) which are always single files
- Maximum depth: 2 levels from any lens root (e.g., `apps/cli.md` or `apps/cli/index.md` + `apps/cli/tui-rendering.md`). No deeper.
- Every directory must contain an `index.md`
- For large repos (50+ source directories or 10+ distinct subsystems), lean toward splitting pages rather than cramming. A 3000-word page covering an entire subsystem is less useful than three focused pages covering its distinct aspects. Critical sub-agents decide whether to create sub-pages based on what they find in the code.
- For small repos, default to single pages and only split when a topic has clearly distinct sub-areas
- Deployment and security start as single pages; expand to directories only if the repo has enough substance

## Naming rules

- Use lowercase filenames with hyphens: `getting-started.md`, not `GettingStarted.md`
- File names use lowercase with hyphens. No spaces, no uppercase.

## Page title rules

Page titles (the `# Heading` at the top of each `.md` file) should be concise noun phrases that match how the team refers to the thing. The section hierarchy already provides context, so titles should not repeat it.

- **Don't prepend directory paths.** Title is "CLI", not "apps/cli — CLI Architecture".
- **Don't append generic suffixes.** Title is "Apps", not "Apps Overview". Title is "Packages", not "Packages — Overview". The only exception is `overview/index.md` which may include the project name (e.g., "Acme platform overview").
- **Don't repeat the parent section name.** A page at `features/sessions.md` is titled "Sessions", not "Features — Sessions".
- **Match the team's vocabulary.** If the team calls it "the daemon", title is "Daemon", not "Background Service Process".
- **Keep it short.** Aim for 1-3 words. If a title needs more, the page probably covers too much and should be split.

## File structure tree

The generated wiki follows this layout:

```
wiki/
├── .wiki-meta.json

# Always present (in this order)
├── index.md                              # Root landing page (serves / for static site generators)
├── overview/                             # Introductory material
│   ├── index.md                          # Project overview
│   ├── architecture.md                   # System architecture with Mermaid diagrams
│   ├── getting-started.md                # Prerequisites, install, build, test, run
│   └── glossary.md                       # Project-specific terms and vocabulary
├── by-the-numbers.md                     # Codebase statistics snapshot
├── lore.md                               # Timeline, eras, deprecated features, rewrites
├── fun-facts.md                          # Easter eggs, origin stories, oldest code
├── how-to-contribute/                    # How to work in this codebase
│   ├── index.md
│   ├── development-workflow.md
│   ├── testing.md
│   ├── debugging.md
│   ├── patterns-and-conventions.md
│   └── tooling.md

# Organizational lenses (use any combination, at least one required)
# Labels mirror the repo's own vocabulary
├── <apps|services|applications>/         # Deployable units
│   ├── index.md
│   ├── <simple-app>.md                   # Single page for simple apps
│   └── <complex-app>/                    # Directory for complex apps
│       ├── index.md
│       └── <sub-topic>.md
├── <systems|modules|subsystems>/         # Internal building blocks
│   ├── index.md
│   ├── <simple-system>.md
│   └── <complex-system>/                 # 3rd level for complex subsystems
│       ├── index.md
│       └── <sub-topic>.md
├── <features|capabilities|workflows>/    # Cross-cutting capabilities
│   ├── index.md
│   ├── <simple-feature>.md
│   └── <complex-feature>/                # Features that span many systems deserve sub-pages
│       ├── index.md
│       └── <sub-topic>.md
├── <packages|libraries|crates>/          # Workspace packages
│   ├── index.md
│   ├── <simple-package>.md
│   └── <complex-package>/
│       ├── index.md
│       └── <sub-topic>.md
├── <primitives|core-concepts|entities>/  # Foundational domain objects
│   ├── index.md
│   └── *.md

# Conditional sections (LLM judgment)
├── api/                                  # If the repo exposes APIs
│   ├── index.md
│   └── *.md
├── deployment.md                         # Single page or directory
├── security.md                           # Single page or directory
├── how-to-monitor/                       # Logging, metrics, tracing, alerting (services only)
│   ├── index.md
│   ├── logging.md                        # Where logs go, how to query, log levels
│   ├── metrics.md                        # What's tracked, dashboards, SLIs
│   ├── tracing.md                        # Distributed tracing, request tracing
│   └── alerting.md                       # Alerts, thresholds, escalation, noisy alerts
├── background/                           # Design decisions, pitfalls, migration context
│   ├── index.md
│   └── *.md
├── cleanup-opportunities/                # Dead code, TODOs, complexity hotspots, stale deps
│   ├── index.md
│   ├── dead-ends.md                      # Unused files, exports, modules
│   ├── todos-and-fixmes.md               # Accumulated TODO/FIXME/HACK comments
│   ├── complexity-hotspots.md            # Largest files, deepest nesting
│   └── dependency-freshness.md           # Outdated or unmaintained dependencies

# Always present (bottom)
├── reference/
│   ├── index.md
│   ├── configuration.md
│   ├── data-models.md
│   └── dependencies.md
└── maintainers.md                        # Subsystem ownership table (conditional, always last)
```

**Rules:**

- Every `.md` file must start with a level-1 heading (`# Title`). The heading serves as the page title for viewers and static site generators. The root `index.md` heading is also used as the site title.
- The root `index.md` is required. It is the only file that serves the root route (`/`); without it, every static site generator returns a 404 on the homepage. Do not list it in `topLevelSections` — it is a landing page, not a content section.
- Every directory must contain an `index.md`.
- File names use lowercase with hyphens. No spaces, no uppercase.
- The `.wiki-meta.json` file is optional metadata (page ordering, generation timestamp) for viewers that support it and is not rendered as a page.
- The four pages inside `overview/` (`index.md`, `architecture.md`, `getting-started.md`, `glossary.md`) are always single files. All other pages can expand into directories with sub-pages.
- Maximum tree depth: 2 levels from any lens root (e.g., `apps/cli/command-structure.md`). No deeper.
- For large repos, critical sub-agents decide whether to split into sub-pages. A complex subsystem like an editor core or extension host should have its own directory with focused sub-pages, not a single monolithic page.
- Maximum 200 pages per wiki run. If a project needs more, prioritize the most important subsystems.

## Meta file (`.wiki-meta.json`)

After generating all pages, create `.wiki-meta.json` in the wiki directory root. The `pageOrder` array is a hint for markdown viewers and static site generators that want to preserve authoring order — it lets a renderer surface pages in the order below rather than falling back to alphabetical sort. List every generated file path in the exact order you want them to appear.

```json
{
  "generatedAt": "2025-01-15T10:30:00Z",
  "pageCount": 42,
  "topLevelSections": ["overview", "by-the-numbers", "lore", "fun-facts", "how-to-contribute", "apps", "systems", "features", "packages", "primitives", "api", "deployment", "security", "how-to-monitor", "background", "cleanup-opportunities", "reference", "maintainers"],
  "pageOrder": [
    "index.md",
    "overview/index.md",
    "overview/architecture.md",
    "overview/getting-started.md",
    "overview/glossary.md",
    "by-the-numbers.md",
    "lore.md",
    "fun-facts.md",
    "how-to-contribute/index.md",
    "how-to-contribute/development-workflow.md",
    "how-to-contribute/testing.md",
    "how-to-contribute/debugging.md",
    "how-to-contribute/patterns-and-conventions.md",
    "how-to-contribute/tooling.md",
    "apps/index.md",
    "apps/cli/index.md",
    "apps/cli/command-structure.md",
    "apps/cli/tui-rendering.md",
    "apps/daemon.md",
    "systems/index.md",
    "systems/auth.md",
    "features/index.md",
    "features/wiki-generation.md",
    "packages/index.md",
    "packages/common.md",
    "primitives/index.md",
    "primitives/session.md",
    "api/index.md",
    "api/rest-endpoints.md",
    "deployment.md",
    "security.md",
    "how-to-monitor/index.md",
    "how-to-monitor/logging.md",
    "how-to-monitor/metrics.md",
    "how-to-monitor/tracing.md",
    "how-to-monitor/alerting.md",
    "background/index.md",
    "background/design-decisions.md",
    "background/pitfalls.md",
    "background/migration-context.md",
    "cleanup-opportunities/index.md",
    "cleanup-opportunities/dead-ends.md",
    "cleanup-opportunities/todos-and-fixmes.md",
    "cleanup-opportunities/complexity-hotspots.md",
    "cleanup-opportunities/dependency-freshness.md",
    "reference/index.md",
    "reference/configuration.md",
    "reference/data-models.md",
    "reference/dependencies.md",
    "maintainers.md"
  ]
}
```

The example above is abbreviated. In practice, list every `.md` file in the wiki directory. The order must match the page ordering defined in [Page ordering](#page-ordering): index.md (landing) → overview → by-the-numbers → lore → fun-facts → how-to-contribute → lenses → conditional → reference → maintainers.
