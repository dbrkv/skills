# Surveying the repository

This reference defines the full survey methodology for reading a repository before writing any wiki pages. Read this during the survey phase of wiki generation.

The survey builds a mental model of the codebase through three mandatory passes, followed by exhaustive subsystem discovery and a coverage cross-check. All three passes are mandatory — skipping the third is the most common cause of a wiki that documents the entities but misses the workflows, policies, and calculations readers actually need to change.

## Contents

- [Pass 1: Structural scan](#pass-1-structural-scan)
- [Pass 2: Deep code scan](#pass-2-deep-code-scan)
- [Pass 3: Business-logic discovery](#pass-3-business-logic-discovery)
- [Exhaustive subsystem discovery](#exhaustive-subsystem-discovery)
- [Often-missed areas](#often-missed-areas)
- [Survey output](#survey-output)
- [Coverage cross-check](#coverage-cross-check)

## Pass 1: Structural scan

Read these files (when they exist):

- `README.md`, `AGENTS.md`, `CONTRIBUTING.md` — project intent and conventions
- `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml` — dependencies and scripts
- `docs/` directory — existing documentation
- Entry points (`src/index.ts`, `main.go`, `app.py`, etc.) — how the application starts
- CI/CD config (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`, etc.)
- Build tool config (`webpack.config.*`, `vite.config.*`, `Makefile`, `build/`, `Gulpfile.*`, etc.)
- Lint/quality config (`eslint.config.*`, custom lint plugins, `rustfmt.toml`, `.golangci.yml`, etc.)
- Directory listing of the project root and key subdirectories

Build a map of:

- **What the project does** — its purpose in one or two sentences
- **Major subsystems** — the main areas of the codebase (e.g., API layer, database models, CLI, frontend components)
- **Key data flows** — how data moves through the system (request → handler → database → response)
- **External dependencies** — databases, APIs, message queues, third-party services
- **Build and test commands** — how to build, test, and run the project

## Pass 2: Deep code scan

The structural scan catches what's visible from directory names and config files. The deep scan catches features, domains, and capabilities that are only visible in the code itself. Probe the codebase for signals that reveal topics the structural scan missed:

- Grep for feature flag names in constants files — each flag often represents a distinct capability worth documenting
- Scan frontend route definitions and page components — each route group is a user-facing feature
- Scan API endpoint groups — each controller or router file represents a domain area
- Look inside `src/features/`, `src/modules/`, `src/domains/`, or equivalent directories — the names and contents reveal product capabilities
- Scan for service classes, event handlers, and job/worker definitions — these reveal background systems
- Check for domain-specific directories that don't map to obvious top-level names
- Look for the domain model even when there's no `domain/` directory. Recurring nouns in class/struct/table names, past-tense event types, and domain-named exceptions (`InsufficientFundsError`, `OverlappingReservationError`) all reveal foundational concepts that may warrant their own `primitives/` pages. See `domain-model.md` for the full discovery playbook.
- Look for business logic, not just domain objects. If you spot a multi-step orchestrator, a branchy decision, a pure calculation, or a cross-aggregate constraint during the deep scan, note it — Pass 3 runs the full discovery.

The goal is to discover the **complete list of topics** the wiki should cover. The structural scan gives you the skeleton; the deep scan fills in the muscle. A feature like "Analytics" might not have its own top-level directory but lives inside `src/features/analytics/` or is revealed by a set of feature flags and API endpoints.

## Pass 3: Business-logic discovery

Passes 1 and 2 find subsystems and domain objects. This pass finds the *behavior* — the workflows, decisions, calculations, and cross-aggregate rules that make the business run. It is mandatory and separate from Pass 2 because business logic is the code readers most often need to change, and it is the easiest to miss: it is defined by what code does, not by where it lives, so it does not gather in any one directory and is invisible to a structural scan. A wiki that documents the entities and skips the logic leaves every reader one refactor away from an expensive mistake.

**Read `business-logic.md` first.** It defines the four signal groups, the behavior-based discovery methods, and the page templates. Run all four groups against the codebase and emit a dedicated **business-logic topic list** — kept separate from the subsystem and domain-object lists because these pages use different templates (workflow / policy / calculation) than the subsystem template:

- **Workflows and processes** — multi-step orchestrators, sagas, queue processors, workflow-engine definitions, background jobs. Signals: a method calling several collaborators in sequence, status fields with many values, retry/compensation code.
- **Decisions and policies** — pricing, eligibility, fraud, access control, strategy/policy classes, rule engines, decision tables. Signals: methods returning a boolean or category (`isEligible`, `shouldApprove`, `classify`), branchy code, config-driven thresholds.
- **Calculations and transformations** — fees, taxes, currency conversion, scoring, proration. Signals: pure functions with arithmetic bodies, lookup tables, verb-named methods (`compute`, `convert`, `score`).
- **Cross-aggregate rules** — invariants spanning multiple aggregates. Signals: application services querying multiple repositories, partial unique indexes, exclusion constraints, advisory locks.

Use the behavior-based discovery methods in `business-logic.md` ("How to find behavioral code") rather than assuming where logic lives. Trace call graphs from every entry point the repo actually has, grep for behavioral lexical patterns (dispatch/publish calls, branching density, retry/compensate keywords), sort by complexity and test density, and inspect the data layer for constraints. Directory and class names (`Service`, `Handler`, `Command`, `Policy`, `Workflow`) are a hint for where to read first, not a filter — teams diverge from framework conventions, especially in long-lived codebases, and a workflow can live in a controller, a model method, or a free function just as easily as in a dedicated service.

Every business-logic topic becomes a planned page using its matching template. These pages usually live under `features/` (user-visible or cross-system) or `systems/` (internal engine or background process). Do not absorb a workflow or policy into the subsystem page of its owning directory — an orchestration method found anywhere in the codebase is a workflow page, not a bullet inside that directory's subsystem page.

## Exhaustive subsystem discovery

After all three passes, walk every top-level source directory (and one level below) to check for subsystems you missed. For each directory that contains its own service, module, or feature, decide:

- **Tier 1** — core subsystems most contributors will encounter. Full dedicated page.
- **Tier 2** — important but specialized. Shorter dedicated page.
- **Tier 3** — niche or thin wrapper. A paragraph in an "Other subsystems" page with directory pointers.

Small repos may only need a few domain pages. Large repos should have as many as the codebase warrants. Do not cap arbitrarily — let the repo's actual structure determine coverage.

## Often-missed areas

After scanning the source tree, check for these commonly overlooked areas:

- **Custom lint/analysis rules** — plugins or config that enforce project-specific conventions
- **Automation workflows** — CI/CD, bots, scheduled jobs, code generation scripts
- **CLI or dev tools** — internal tools, scripts in `scripts/`, `tools/`, or `bin/`
- **Test infrastructure** — custom test frameworks, fixtures, or automation harnesses beyond standard test runners
- **Multi-language components** — if the repo has code in a second language (e.g., Rust CLI in a TypeScript project), document it

If any of these are non-trivial, they deserve coverage — either as their own page or as a section in a related page.

## Survey output

At the end of the survey, produce a **survey context document** — a compact summary that will be shared with sub-agents. This document should include:

- **Repo summary** — 3-5 sentences: what the project is, its tech stack, and high-level structure
- **Architecture overview** — major components and how they connect
- **Discovered topics** — the complete list of features, systems, apps, packages, and primitives found during both scan passes
- **Business-logic topics** — the workflows, policies, calculations, and cross-aggregate rules found in Pass 3. Each entry is tagged with its category (workflow / policy / calculation / cross-aggregate) and the source files that implement it. Kept as a separate list from subsystem and domain topics so each can be planned with the matching page template.
- **Key patterns** — coding conventions, error handling patterns, testing patterns
- **Glossary seeds** — project-specific terms encountered during the scan
- **Directory-to-purpose map** — which source directories map to which topics

## Coverage cross-check

Before moving to planning, reconcile three independent topic sources to ensure nothing is missed:

**Source A: Discovered topics.** The topics found during Pass 1 (structural scan) and Pass 2 (deep code scan). These include cross-cutting features that don't map to a single directory (e.g., "LLM integration" spanning multiple packages, "authentication" touching frontend, backend, and CLI).

**Source B: Directory enumeration.** For each lens that applies to the repo, run `ls` on the corresponding source directories and list every subdirectory:

- For apps: list every directory under `apps/` (or the repo's equivalent)
- For packages: list every workspace package directory
- For features: list every subdirectory under the feature directory (e.g., `src/features/`, `packages/frontend/src/features/`, or wherever the repo organizes features)
- For systems: list the top-level source directories that contain service or module code

**Source C: Behavioral code.** For every method or function identified in Pass 3 that orchestrates (calls multiple collaborators in sequence), decides (returns a choice with significant branching), or computes (a pure transformation), record it as a candidate business-logic page — wherever it lives, regardless of the surrounding directory or class name. Each must map to a workflow / policy / calculation page or an explicit skip with a reason. A non-trivial behavioral method with no business-logic page is a gap that must be justified: this is where revenue, compliance, and fraud logic actually live, and it is the code readers most often need to change.

**Reconciliation:** Merge all three lists. For every item on any list, decide:

1. **Wiki page** — the item becomes a planned page (or section within a page)
2. **Skip with reason** — the item is intentionally excluded, with a specific reason (e.g., "empty directory — 0 source files", "deprecated — only test fixtures remain", "thin wrapper — covered in parent package page", "internal tooling — 3 files, not worth a standalone page")

The discovered topics catch things that directories miss (cross-cutting concerns, emergent patterns). The directory enumeration catches things that discovery misses (features the agent didn't encounter in the files it read). The behavioral-code pass catches the logic that both miss (orchestrators and policies buried inside any layer of the codebase, conventionally named or not). Together they produce comprehensive coverage.

Silent omissions are not acceptable. If a source directory exists with non-trivial code and has no wiki topic, that's a gap that must be justified.
