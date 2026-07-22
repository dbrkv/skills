# Threat modeling reference (Phase 1)

This reference covers Phase 1 of the security review: analyzing a repository and producing a STRIDE-based threat model. The threat model is the persistent context that Phase 2 (scanning) and Phase 3 (validation) reason against, so it must be specific to the codebase's actual architecture, tech stack, and data flows.

Write two files:
- `.security/threat-model.md` — the threat model document (natural language, LLM-optimized)
- `.security/config.json` — machine-readable configuration (severity thresholds, enabled patterns)

## Table of contents

1. [When to (re)generate](#when-to-regenerate)
2. [Inputs](#inputs)
3. [Step 1: Analyze the repository structure](#step-1-analyze-the-repository-structure)
4. [Step 2: Identify trust boundaries](#step-2-identify-trust-boundaries)
5. [Step 3: Inventory critical assets](#step-3-inventory-critical-assets)
6. [Step 4: Apply STRIDE analysis](#step-4-apply-stride-analysis)
7. [Step 5: Document vulnerability patterns](#step-5-document-vulnerability-patterns)
8. [Step 6: Write the output files](#step-6-write-the-output-files)
9. [Threat model document template](#threat-model-document-template)
10. [Success criteria](#success-criteria)
11. [Verification](#verification)

## When to (re)generate

- **First-time setup** — new repository needs an initial threat model
- **Architecture changes** — significant changes to components, APIs, or data flows
- **Security audit** — periodic review or compliance requirement
- **Missing or stale** — no threat model exists, or it's over 90 days old

## Inputs

| Input | Description | Required |
|---|---|---|
| Repository path | Root directory to analyze | Yes (default: current directory) |
| Existing threat model | Path to existing `.security/threat-model.md` if updating | No |
| Compliance requirements | Frameworks to consider (SOC2, GDPR, HIPAA, etc.) | No |
| Security contacts | Email addresses for security team notifications | No |

## Step 1: Analyze the repository structure

Scan the codebase to understand the system.

1. **Identify languages and frameworks.** Check `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, etc. Note the primary tech stack (e.g., Next.js, Django, Go microservices).

2. **Map components and services.** Look for `apps/`, `services/`, `packages/` directories. Identify entry points: API routes, CLI commands, web handlers. Note databases, caches, message queues.

3. **Identify external interfaces.** HTTP endpoints (REST, GraphQL), file upload handlers, webhook receivers, OAuth/SSO integrations, CLI commands that accept user input.

4. **Trace data flows.** How does user input enter the system? Where is sensitive data stored? What external services are called?

## Step 2: Identify trust boundaries

Define security zones.

1. **Public Zone** (untrusted) — all external HTTP endpoints, public APIs without authentication, user-uploaded files.

2. **Authenticated Zone** (partially trusted) — endpoints requiring a valid session/token, user-specific data access, rate-limited APIs.

3. **Internal Zone** (trusted) — service-to-service communication, admin-only endpoints, database connections, secrets management.

Document where trust boundaries exist and what validates transitions between zones.

## Step 3: Inventory critical assets

Classify data by sensitivity.

1. **PII** — user emails, names, addresses, phone numbers. Document protection measures.
2. **Credentials and secrets** — password hashes, API keys, OAuth tokens, JWT signing keys, encryption keys. Document rotation policies.
3. **Business-critical data** — transaction records, customer data, proprietary algorithms. Document access controls.

## Step 4: Apply STRIDE analysis

For each major component, analyze threats in all six categories. For each identified threat: describe the attack scenario, list vulnerable components, show code patterns to look for, note existing mitigations, identify gaps, and assign severity (CRITICAL/HIGH/MEDIUM/LOW) and likelihood.

#### S - Spoofing

Can attackers impersonate users or services? Are authentication mechanisms secure? Look for: weak session handling, API key exposure, missing MFA, JWT vulnerabilities (none algorithm, weak secrets).

#### T - Tampering

Can attackers modify data in transit or at rest? Look for: SQL injection, XSS, mass assignment, missing input validation, command injection, path traversal, XXE.

#### R - Repudiation

Can users deny actions they performed? Look for: missing audit logs, insufficient logging, no immutable trails.

#### I - Information disclosure

Can attackers access data they shouldn't? Look for: IDOR, verbose errors, hardcoded secrets, data leaks in logs.

#### D - Denial of service

Can attackers disrupt service availability? Look for: missing rate limits, resource exhaustion, algorithmic complexity.

#### E - Elevation of privilege

Can attackers gain unauthorized access levels? Look for: missing authorization checks, role manipulation, privilege escalation, RBAC bypass.

## Step 5: Document vulnerability patterns

Create a library of code patterns specific to this codebase's tech stack, showing both vulnerable and safe variants:

```python
# Example: SQL Injection patterns for Python
# VULNERABLE
sql = f"SELECT * FROM users WHERE id = {user_id}"

# SAFE
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

Include patterns for SQL injection, XSS, command injection, path traversal, authentication bypass, and IDOR.

## Step 6: Write the output files

### `.security/threat-model.md`

Use the [template below](#threat-model-document-template) to generate a comprehensive threat model with: system overview, trust boundaries and security zones, attack surface inventory, critical assets classification, STRIDE threat analysis for each component, vulnerability pattern library, security testing strategy, assumptions and accepted risks, and a version changelog.

The document should be written in natural language with code examples, optimized for LLM comprehension.

### `.security/config.json`

```json
{
  "threat_model_version": "1.0.0",
  "last_updated": "<ISO timestamp>",
  "security_team_contacts": [],
  "compliance_requirements": [],
  "scan_frequency": "on_commit",
  "severity_thresholds": {
    "block_merge": ["CRITICAL"],
    "require_review": ["HIGH", "CRITICAL"],
    "notify_security_team": ["CRITICAL"]
  },
  "vulnerability_patterns": {
    "enabled": [
      "sql_injection",
      "xss",
      "command_injection",
      "path_traversal",
      "auth_bypass",
      "idor"
    ],
    "custom_patterns_path": null
  }
}
```

Customize based on detected compliance requirements (from docs, configs, or user input), security team contacts (if provided), and tech stack (enable relevant vulnerability patterns).

## Threat model document template

This defines the structure for `.security/threat-model.md`. Follow this structure and replace all `{placeholder}` values with actual content derived from the repository.

```markdown
# Threat Model for {Repository Name}

**Last Updated:** {YYYY-MM-DD}
**Version:** {X.Y.Z}
**Methodology:** STRIDE + Natural Language Analysis

---

## 1. System Overview

### Architecture Description

This is a {type of application} that allows users to {primary functions}. The system is built using {technology stack} and consists of {number} main components:

1. **{Component Name}** - {Description of what it does and why it exists}
2. **{Component Name}** - {Description of what it does and why it exists}
3. **{Component Name}** - {Description of what it does and why it exists}

### Key Components

| Component | Purpose | Security Criticality | Attack Surface |
|---|---|---|---|
| {Component} | {Purpose} | {HIGH/MEDIUM/LOW} | {Entry points} |

### Data Flow

When a user {action}, the system {process}. This involves {data flow description}. The data is validated at {points} and authenticated using {mechanism}.

---

## 2. Trust Boundaries & Security Zones

The system has **{N} trust zones**:

1. **Public Zone** - Untrusted external users and systems
   - Assumes: Malicious input, no authentication
   - Entry Points: {List all public entry points}

2. **Authenticated Zone** - Verified users with valid sessions
   - Assumes: User may be malicious but has valid credentials
   - Entry Points: {List protected endpoints}

3. **Internal Zone** - Service-to-service communication
   - Assumes: Services are trusted but data may be poisoned
   - Entry Points: {List internal APIs, databases}

### Authentication & Authorization

Users authenticate using {method}. Sessions are managed via {mechanism} with {expiry}. Authorization is enforced using {RBAC/ABAC/custom} at {enforcement points}.

**Critical Security Controls:**
- {Control 1}
- {Control 2}
- {Control 3}

---

## 3. Attack Surface Inventory

### Public HTTP Endpoints

- `{METHOD} {/path}` - {Description}
  - **Input:** {Parameters and types}
  - **Validation:** {What validation is performed}
  - **Risk:** {Potential attack vectors}

### File Upload Endpoints

- `{METHOD} {/path}` - {Description}
  - **Input:** {File types, metadata}
  - **Validation:** {Type whitelist, size limits, malware scan}
  - **Risk:** {Malicious upload, path traversal, XXE}

### Data Input Vectors

The system accepts user input from:
1. {Input vector 1}
2. {Input vector 2}
3. {Input vector 3}

---

## 4. Critical Assets & Data Classification

### PII (Personally Identifiable Information)
- **{Data type}** - {How it's used}

**Protection Measures:** {Encryption, access controls, logging}

### Credentials & Secrets
- **{Secret type}** - {How it's protected}

**Protection Measures:** {Secrets manager, rotation policy, never logged}

### Business-Critical Data
- **{Data type}** - {Why it's critical}

---

## 5. Threat Analysis (STRIDE Framework)

For each category below, document: the threat scenario, vulnerable components, the attack vector as numbered steps, the code pattern to look for (vulnerable + safe), existing mitigations, gaps, severity, and likelihood.

### S - Spoofing Identity
An attacker pretends to be someone or something they're not to gain unauthorized access.

{Threat entries following the structure above}

### T - Tampering with Data
Unauthorized modification of data in memory, storage, or transit.

{Threat entries}

### R - Repudiation
Users can deny performing actions because there's insufficient audit logging.

{Threat entries}

### I - Information Disclosure
Exposing information to users who shouldn't have access.

{Threat entries}

### D - Denial of Service
Attacks that prevent legitimate users from accessing the system.

{Threat entries}

### E - Elevation of Privilege
Gaining higher privileges than intended.

{Threat entries}

---

## 6. Vulnerability Pattern Library

This section contains code patterns that indicate vulnerabilities. When analyzing code: look for these patterns, consider the context (is input sanitized earlier?), check if mitigations are in place, and cross-reference with the STRIDE threats above.

### SQL Injection Patterns
```{language}
# PATTERN 1: String concatenation in SQL
{vulnerable pattern}

# SAFE ALTERNATIVE:
{safe pattern}
```

### XSS (Cross-Site Scripting) Patterns
### Command Injection Patterns
### Path Traversal Patterns
### Authentication Bypass Patterns
### IDOR Patterns

{Each with vulnerable + safe variants}

---

## 7. Security Testing Strategy

| Tool | Purpose | Frequency |
|---|---|---|
| {SAST tool} | Static analysis | Every commit |
| {Dependency scanner} | Vulnerable dependencies | Daily |
| {Secrets detection} | Leaked credentials | Every commit |
| {DAST tool} | Dynamic testing | Weekly on staging |

Manual security reviews are required for HIGH/CRITICAL findings, new authentication/authorization code, changes to cryptographic functions, and admin privilege management changes.

---

## 8. Assumptions & Accepted Risks

### Security Assumptions
1. **{Assumption}** - {Why we assume this is secure}

### Accepted Risks
1. **{Risk}** - {Why we're accepting it, mitigation timeline if any}

---

## 9. Threat Model Changelog

### Version {X.Y.Z} ({YYYY-MM-DD})
- Initial threat model created
- STRIDE analysis completed for all components
- Vulnerability pattern library established
```

### Severity and likelihood ratings

| Severity | Definition |
|---|---|
| **CRITICAL** | Immediate exploitation possible, severe impact (data breach, RCE) |
| **HIGH** | Exploitation likely, significant impact (auth bypass, privilege escalation) |
| **MEDIUM** | Exploitation requires specific conditions, moderate impact |
| **LOW** | Difficult to exploit, minimal impact |

| Likelihood | Definition |
|---|---|
| **VERY HIGH** | Trivial to exploit, commonly targeted |
| **HIGH** | Easy to exploit with basic skills |
| **MEDIUM** | Requires specific knowledge or conditions |
| **LOW** | Difficult to exploit, rarely targeted |

### LLM optimization tips

For maximum effectiveness with downstream scan and validation phases: use explicit code patterns (LLMs match patterns better than prose), write attack vectors as numbered steps, use consistent headings for targeted retrieval, and cross-reference threats to specific code locations when known.

## Success criteria

The threat model is complete when:

- [ ] `.security/threat-model.md` exists with all sections populated
- [ ] `.security/config.json` exists with valid JSON
- [ ] All major components have STRIDE analysis
- [ ] Vulnerability patterns match the tech stack
- [ ] Document is written in natural language (LLM-readable)
- [ ] No placeholder text remains

## Verification

Run these checks before completing:

```bash
# Verify threat model exists and is non-empty
test -s .security/threat-model.md && echo "OK Threat model exists"

# Verify config is valid JSON
jq . .security/config.json > /dev/null && echo "OK Config is valid JSON"

# Check threat model has key sections
grep -q "## 1. System Overview" .security/threat-model.md && echo "OK Has System Overview"
grep -q "## 5. Threat Analysis" .security/threat-model.md && echo "OK Has Threat Analysis"
grep -q "## 6. Vulnerability Pattern Library" .security/threat-model.md && echo "OK Has Pattern Library"
```

## External references

- [STRIDE threat modeling](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [OWASP threat modeling](https://owasp.org/www-community/Threat_Modeling)
