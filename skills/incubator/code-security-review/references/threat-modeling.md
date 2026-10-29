# Threat modeling (Phase 1)

How to create or update `docs/security/threat-model.md`: the STRIDE model of the repository that every review reasons against. It must describe this codebase's real architecture, stack, and data flows. A generic model is worse than none, because it hides what was never examined.

The model is a normal project document. It is written in plain language for the people and agents who read it, reviewed like code, and committed.

## When to create or update

- **Missing**: no `docs/security/threat-model.md` yet, in a full audit or when the user asks for the model. A diff review only offers to create it.
- **Architecture changed**: a component, entry point, external integration, or trust boundary was added or removed.
- **Stale**: *Last Updated* is more than 90 days old.
- **Asked**: the user wants it refreshed.

**Updating means editing, not regenerating.** Keep sections that are still true, change the ones that are not, keep *Accepted Risks* as is unless the owner says otherwise, bump the version, and add a changelog entry that says what changed.

## Step 1: Understand the system

1. **Stack.** Read the dependency manifests and note the languages, frameworks, and their versions.
2. **Components.** Find the applications, services, clients, and packages. Note databases, caches, queues, background workers, and third-party SDKs embedded in clients.
3. **Entry points.** HTTP routes and controllers, API handlers (REST, GraphQL, RPC), server actions, webhooks, file uploads, OAuth/SSO callbacks, CLI commands, queue consumers, scheduled jobs.
4. **Data flows.** Where user input enters, where sensitive data is stored, which external services are called and with what credentials.
5. **Existing documentation.** Architecture decision records, security guidelines, and agent instructions often state trust decisions the code alone does not show. Cite them; do not copy them.

## Step 2: Trust boundaries

Describe the security zones and what validates every crossing between them. A typical system has:

1. **Public zone (untrusted).** Anonymous entry points, uploaded files, anything shipped to a client (browser, mobile app, desktop app), and other apps or processes on the same device that can call into a client.
2. **Authenticated zone (partly trusted).** Endpoints that need a valid session or token. The user may still be malicious. Authorization is per resource, not per login.
3. **Privileged zone.** Administrator and staff functions, internal tools.
4. **Internal zone (trusted).** Service-to-service calls, databases, secret stores.

For each boundary, name the code that enforces it (file, class, middleware, guard).

## Step 3: Critical assets

1. **Personal data**: names, emails, phone numbers, addresses, documents, messages, location.
2. **Credentials and secrets**: password hashes, sessions, API keys, OAuth tokens, signing and encryption keys.
3. **Business-critical data and actions**: payments, bookings, balances, permissions, anything that moves money or changes who can access what.

Note where each is stored and which code guards it.

## Step 4: STRIDE per component

For each major component, go through all six categories. For each real threat, record: the scenario, the components involved, the attack as numbered steps, the code pattern to look for (vulnerable and safe, in this repository's language), existing mitigations with their location, gaps, severity, and likelihood.

- **S, Spoofing.** Can someone impersonate a user or service? Session handling, token validation, password reset, OAuth state, API keys.
- **T, Tampering.** Can data be changed in transit or at rest? Injection (SQL, command, template), XSS, mass assignment, path traversal, XXE, unsigned or unverified data.
- **R, Repudiation.** Can a user deny an action? Missing audit trail for money, permissions, and administrative actions.
- **I, Information disclosure.** Can someone read what they should not? IDOR, over-broad serialization, verbose errors, secrets in code or logs, data in client bundles.
- **D, Denial of service.** Can availability be disrupted? Missing limits on expensive operations, unbounded uploads or queries, abuse of paid external calls.
- **E, Elevation of privilege.** Can someone gain rights they should not have? Missing authorization checks, role manipulation, privilege escalation through parameters.

A category with no real threat for a component says so in one line. Do not invent threats to fill a section.

## Step 5: Write the file

Create `docs/security/` if needed and write `docs/security/threat-model.md` with the template below. Replace every `{placeholder}`. Use the repository's own language and framework in code patterns. Point to real files.

```markdown
# Threat model: {Repository name}

**Last Updated:** {YYYY-MM-DD}
**Version:** {X.Y.Z}
**Method:** STRIDE

## 1. System overview

{What the system does, for whom, and how it is built, in a few paragraphs.}

| Component | Purpose | Criticality | Entry points |
|---|---|---|---|
| {component} | {purpose} | {HIGH/MEDIUM/LOW} | {routes, handlers, jobs} |

### Data flow

{How a typical request moves through the system, where input is validated, where identity and permissions are checked.}

## 2. Trust boundaries

1. **Public zone**: {who, which entry points}
2. **Authenticated zone**: {who, which entry points, how sessions work}
3. **Privileged zone**: {who, which functions}
4. **Internal zone**: {services, data stores}

### Authentication and authorization

{How users authenticate, how sessions or tokens are issued and checked, where authorization decisions are made (file, class, mechanism).}

## 3. Attack surface inventory

### {Entry point group, e.g. public HTTP routes}

- `{METHOD} {/path}` ({file}): {what it does}. Input: {parameters}. Checks: {validation, authorization}. Risk: {what could go wrong}.

{Repeat per group: authenticated routes, admin routes, webhooks, uploads, background jobs, client-side code.}

## 4. Critical assets

| Asset | Where it lives | Who may read or change it | Guarded by |
|---|---|---|---|
| {asset} | {table, store, file} | {roles} | {code} |

## 5. Threats (STRIDE)

### S: Spoofing
{Threat entries: scenario, components, attack steps, vulnerable and safe pattern, mitigations with location, gaps, severity, likelihood.}

### T: Tampering
### R: Repudiation
### I: Information disclosure
### D: Denial of service
### E: Elevation of privilege

## 6. Vulnerability patterns for this codebase

{Vulnerable and safe variants in this repository's language and framework, for the patterns that matter here: injection, XSS, authorization (IDOR), authentication, file handling, deserialization.}

## 7. Assumptions

1. **{Assumption}**: {why it holds; where it is enforced or who stated it}

## 8. Accepted risks

Findings the owner has accepted or dismissed. Reviews suppress a finding only when file, type, and where all match.

| File | Type | Where | Reason | Accepted by | Date |
|---|---|---|---|---|---|
| {path} | {e.g. IDOR, CWE-639} | {short description of the spot} | {why it is accepted} | {name} | {YYYY-MM-DD} |

## 9. Changelog

### {X.Y.Z} ({YYYY-MM-DD})
- {What changed and why}
```

### Severity and likelihood

| Severity | Definition |
|---|---|
| **CRITICAL** | Exploitable now, severe impact (data breach, RCE, account takeover) |
| **HIGH** | Likely exploitable, significant impact (authorization bypass, privilege escalation) |
| **MEDIUM** | Needs specific conditions, moderate impact |
| **LOW** | Hard to exploit, minimal impact |

| Likelihood | Definition |
|---|---|
| **HIGH** | Easy to exploit with basic skills, commonly targeted |
| **MEDIUM** | Needs specific knowledge or conditions |
| **LOW** | Hard to exploit, rarely targeted |

## Done when

- [ ] Every component in the overview table has STRIDE coverage, or a one-line "no real threat"
- [ ] Every trust boundary names the code that enforces it
- [ ] Code patterns use this repository's language and framework
- [ ] No `{placeholder}` remains
- [ ] For an update: *Accepted Risks* preserved, version bumped, changelog entry added
