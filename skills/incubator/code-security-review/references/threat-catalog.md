# Threat catalog

The skill's stable threat taxonomy. Classes have their own IDs — they survive renumbering of external lists. STRIDE remains the spine of the threat model and the summary (`by_stride`); the catalog is what detection and validation actually walk, because its entries are cohesive (one reasoning template per class). OWASP categories are never stored in artifacts: they are computed at report time from `mappings.md`.

Two phases use this file:

- **Scan (Phase 2)** walks the applicable classes per file and assigns each finding a `catalog_class`, a CWE from the class anchors, and the class's default STRIDE (unless an override rule fires). The trust rules below shape recall — they say what counts as exposed and trusted.
- **Validation (Phase 3)** receives the class entry and the trust rules in every validator bundle. The control essence tells the refuter what to look for; the rules settle verdicts where precedents would mislead.

## Table of contents

1. [Trust rules R1–R10](#trust-rules-r1r10)
2. [Class overview](#class-overview)
3. [Applicability](#applicability)
4. [Class entries](#class-entries)
5. [Editions of external lists](#editions-of-external-lists)
6. [config.json compatibility](#configjson-compatibility)

## Trust rules R1–R10

Universal rules of trust. They apply in the scan (shaping what is even considered — recall) and in validation (settling the verdict). **On conflict, a rule wins over a precedent or a hard exclusion; a precedent survives wherever it does not contradict a rule.**

- **R1.** Everything shipped to a client — web bundle, binary, application package, public configuration — is public, including configuration values and build-time variables. The "environment variables are trusted" precedent applies only to values that stay on the server.
- **R2.** Data on a device or in a client is an asset. Its protection is determined by who else can read it (other applications, backups, the device owner with elevated rights, third-party scripts on the page) — not by the fact that "it's on the client". This refines the hard exclusion "secrets stored on disk if properly secured".
- **R3.** Client-side checks are not a control for server resources. Access is verified where the resource lives.
- **R4.** Untrusted content that has access to privileged host capabilities (embedded web content, plugins, third-party scripts) is checked for origin at every call, not once at load time.
- **R5.** Entry points that other software on the same device or in the same browser can call (inter-process calls, link and scheme handlers, cross-window messaging) are treated as unauthenticated until the code proves otherwise.
- **R6.** Framework protections (escaping, parameterization, CSRF tokens) apply only to paths that go through the framework. Code that bypasses the framework is unprotected until proven otherwise.
- **R7.** When one contract has multiple implementations (platforms, adapters, drivers), each is checked separately; a control present in one does not extend to the others.
- **R8.** Comparisons that rely on implicit type coercion or normalization inside a security decision are suspicious.
- **R9.** Controls outside the repository (proxies, CDNs, cloud policies, platform settings) are neither present nor absent. If the deciding fact lies outside the repository, the verdict is `NEEDS_MANUAL_REVIEW` naming that fact.
- **R10.** Self-harm — a user damaging only themselves within their own rights — is not a trust-boundary crossing and not a finding.

## Class overview

| ID | Threat (one phrase) | Default STRIDE | CWE anchors | Detector |
|---|---|---|---|---|
| INJ | Untrusted data is interpreted as code, a query, a command, markup, or a path | Tampering | 74; 89, 78, 79, 94, 943, 1336, 22, 611, 1321 | D1 |
| OUTBOUND | The server performs a request to an address the attacker controls | ElevationOfPrivilege | 918 | D1 |
| INTEGRITY | Data or code is accepted without authenticity verification (deserialization, updates, signatures) | Tampering | 502, 345, 494, 347 | D1 |
| AUTHN | Who is acting is not established, or weakly established | Spoofing | 287, 306, 307, 640 | D2 |
| SESSION | A session or token can be forged, stolen, or never expires | Spoofing | 384, 613, 1004, 614 | D2 |
| AUTHZ-OBJ | Access to someone else's object through a controllable identifier | ElevationOfPrivilege ¹ | 639, 862 | D2 |
| AUTHZ-FUNC | Calling a function or acting in a role above one's rights | ElevationOfPrivilege | 862, 863, 269 | D2 |
| AUTHZ-PROP | Reading or writing object properties above one's rights (mass assignment, extra fields in responses) | ElevationOfPrivilege ¹ | 915, 213 | D2 |
| LOGIC | Business-process invariants are violated (step order, races, limits, prices) | Tampering | 840, 362 | D2 |
| SECRETS | Secrets in code, history, or shipped artifacts | InfoDisclosure | 798, 540 | D3 |
| DATA-AT-REST | Sensitive data is stored where someone not entitled can read it | InfoDisclosure | 312, 922 | D3 |
| CRYPTO | Weak or misapplied cryptography, unprotected transport, wrong certificate verification | InfoDisclosure | 327, 326, 330, 319, 295 | D3 |
| CONFIG | Insecure configuration in the repository: CORS, debugging, flags, policies | InfoDisclosure | 942, 489, 1021 | D4 |
| EXPOSURE | Sensitive data in responses, errors, logs | InfoDisclosure | 200, 209, 532 | D4 |
| EXCEPTIONAL | An error path leaves the system open or inconsistent (fail-open) | ElevationOfPrivilege | 755, 636 | D4 |
| SUPPLY | Vulnerable or unsupported dependencies | — (in `dependency_findings`) | 1395, 1104 | D5 |
| INBOUND-LOCAL | An entry point callable by other software on the device or in the browser, without sender verification | Spoofing | 926, 939, 346 | D6 |
| EMBEDDED | Untrusted embedded content gains privileged host capabilities | ElevationOfPrivilege | 749, 829, 346 | D6 |
| RESOURCE | Unbounded resource consumption | DoS | 400, 770, 1333, 799 | D7 |
| ACCOUNTABILITY | Security-relevant actions are not recorded, or are recorded forgeably | Repudiation | 778, 117, 223 | D7 |

¹ If only reading is demonstrated, the STRIDE override is `InfoDisclosure`, recorded in `stride_override_reason`.

The **Detector** column shows the fan-out grouping used in Phase 2 detection (see `orchestration.md`): in fan-out mode one subagent runs per detector over its classes; in compact mode the same detectors run as sequential passes under identical contracts.

## Applicability

- **Always on:** INJ, OUTBOUND, INTEGRITY, AUTHN, SESSION, AUTHZ-OBJ, AUTHZ-FUNC, AUTHZ-PROP, LOGIC, SECRETS, DATA-AT-REST, CRYPTO, CONFIG, EXPOSURE, EXCEPTIONAL, RESOURCE, ACCOUNTABILITY.
- **SUPPLY** — when dependency manifests or lockfiles exist (its findings land in `dependency_findings`, not the code-finding flow).
- **INBOUND-LOCAL, EMBEDDED** — when the code contains local entry surfaces (deep links, custom schemes, IPC handlers, cross-window messaging) or embeds untrusted content with host bridges. In the absence of a scout phase, the scan decides applicability from the code it reads.
- Under R1/R2, SECRETS and DATA-AT-REST apply with full force to anything shipped to a client or stored on a device — the "it's just client config" reflex is not a control.

## Class entries

Each entry: the threat, the essence of the control (what "fixed" looks like), STRIDE default and override rule, CWE anchors, and reference material. References name OWASP Cheat Sheet Series sheets and ASVS chapters by name — requirement numbers change across major versions, names do not.

### INJ — Injection
Untrusted data is interpreted as code, a query, a command, markup, or a path.
Control: separation of data and code — parameterized queries, context-aware output encoding, argv lists without a shell, resolved and rooted paths. Not blacklisting dangerous characters.
STRIDE: Tampering (default). CWE anchors: 74; 89, 78, 79, 94, 943, 1336, 22, 611, 1321.
Refs: Cheat Sheets "Injection Prevention", "SQL Injection Prevention", "Cross Site Scripting Prevention", "OS Command Injection Defense"; ASVS chapters "Validation, Sanitization and Encoding", "Files and Resources".

### OUTBOUND — Server-side request forgery
The server performs a request to an address the attacker controls.
Control: the server decides where it connects, not the request — allowlists of hosts and schemes, no raw user-supplied URLs, normalization before any network call.
STRIDE: ElevationOfPrivilege (the server's network position is abused). CWE: 918.
Refs: Cheat Sheet "Server Side Request Forgery Prevention"; ASVS chapter "Validation, Sanitization and Encoding".

### INTEGRITY — Unverified data or code
Data or code is accepted without authenticity verification — native deserialization of untrusted bytes, unsigned updates, unverified signatures or webhooks.
Control: verify provenance before trusting — signatures pinned to a trusted source, checksums, safe data formats; never deserialize untrusted bytes with a native format.
STRIDE: Tampering. CWE: 502, 345, 494, 347.
Refs: Cheat Sheets "Deserialization", "Securing Update Pipelines"; ASVS chapter "Software Integrity" (or " integrity verification" topic).

### AUTHN — Authentication
Who is acting is not established, or weakly established.
Control: prove who is acting before anything else — strong authenticators, no default or anonymous paths on sensitive operations, errors that do not leak which factor failed.
STRIDE: Spoofing. CWE: 287, 306, 307, 640.
Refs: Cheat Sheets "Authentication"; ASVS chapter "Authentication".

### SESSION — Session management
A session or token can be forged, stolen, or never expires.
Control: sessions are bearer credentials — generated unpredictably, bound to the owner, expiring, revocable server-side, rotated on privilege change.
STRIDE: Spoofing. CWE: 384, 613, 1004, 614.
Refs: Cheat Sheet "Session Management"; ASVS chapter "Session Management".

### AUTHZ-OBJ — Object-level authorization
Access to someone else's object through a controllable identifier (IDOR).
Control: every object access verifies the caller's relationship to that object — ownership or an explicit grant — at the data-access point, not in the client.
STRIDE: ElevationOfPrivilege; override InfoDisclosure when only reading is demonstrated (record `stride_override_reason`). CWE: 639, 862.
Refs: Cheat Sheet "Insecure Direct Object Reference Prevention"; ASVS chapter "Access Control".

### AUTHZ-FUNC — Function-level authorization
Calling a function or acting in a role above one's rights.
Control: every privileged function checks the caller's right at the server-side enforcement point, regardless of what the UI shows or hides.
STRIDE: ElevationOfPrivilege. CWE: 862, 863, 269.
Refs: Cheat Sheet "Authorization"; ASVS chapter "Access Control".

### AUTHZ-PROP — Property-level authorization
Reading or writing object properties above one's rights — mass assignment, extra fields in responses.
Control: field allowlists for input binding and output shaping; never pass a request body straight through to a model or serializer.
STRIDE: ElevationOfPrivilege; override InfoDisclosure when only reading is demonstrated (record `stride_override_reason`). CWE: 915, 213.
Refs: Cheat Sheets "Mass Assignment"; ASVS chapter "Access Control".

### LOGIC — Business logic
Business-process invariants are violated — step order, races, limits, prices.
Control: server-side enforcement of process invariants — state machines for step order, server-computed prices and limits, idempotency and locking for concurrent flows.
STRIDE: Tampering. CWE: 840, 362.
Refs: Cheat Sheet "Abuse Case"; ASVS chapter "Business Logic" (validation topic).

### SECRETS — Hardcoded secrets
Secrets in code, history, or shipped artifacts.
Control: secrets live in a secrets manager or server-only configuration — never in code, never in history, never in anything shipped to a client (R1).
STRIDE: InfoDisclosure. CWE: 798, 540.
Refs: Cheat Sheets "Secrets Management", "Password Storage"; ASVS chapter "Storage Cryptography / Secrets".

### DATA-AT-REST — Stored data
Sensitive data is stored where someone not entitled can read it.
Control: sensitive data at rest is encrypted or permission-scoped so only entitled components can read it; on devices, assume other readers exist (R2).
STRIDE: InfoDisclosure. CWE: 312, 922.
Refs: Cheat Sheet "Cryptographic Storage"; ASVS chapter "Data Protection".

### CRYPTO — Cryptography
Weak or misapplied cryptography, unprotected transport, wrong certificate verification.
Control: vetted primitives and protocols with library defaults — no homemade crypto, no disabled verification, TLS everywhere data moves.
STRIDE: InfoDisclosure. CWE: 327, 326, 330, 319, 295.
Refs: Cheat Sheets "Cryptographic Storage", "Transport Layer Protection"; ASVS chapters "Storage Cryptography", "Communications Security".

### CONFIG — Configuration
Insecure configuration in the repository: CORS, debugging, flags, policies.
Control: repository configuration is the most permissive artifact the attacker gets — debug off, CORS scoped to real origins, least privilege by default; anything that may be tightened outside the repo follows R9.
STRIDE: InfoDisclosure. CWE: 942, 489, 1021.
Refs: Cheat Sheets " CORS", "Security Headers"; ASVS chapter "Configuration and Infrastructure".

### EXPOSURE — Information exposure
Sensitive data in responses, errors, logs.
Control: responses, errors, and logs carry the minimum — no stack traces to clients, no internal identifiers, no sensitive fields where an unauthorized reader can see them.
STRIDE: InfoDisclosure. CWE: 200, 209, 532.
Refs: Cheat Sheets "Error Handling", "Logging"; ASVS chapters "Error Handling and Logging", "Data Protection".

### EXCEPTIONAL — Mishandled exceptional conditions
An error path leaves the system open or inconsistent — fail-open.
Control: fail closed — error paths deny, clean up, and leave consistent state; never fall through to an open or half-applied state.
STRIDE: ElevationOfPrivilege. CWE: 755, 636.
Refs: Cheat Sheet "Error Handling"; ASVS chapter "Error Handling and Logging".

### SUPPLY — Dependencies
Vulnerable or unsupported dependencies.
Control: dependencies are code — known versions, lockfiles, vulnerability monitoring, and a reachability check before patching. Findings live in `dependency_findings`, not the code-finding flow.
STRIDE: — (dependency track). CWE: 1395, 1104.
Refs: Cheat Sheet "Dependency Management"; ASVS "Software Lifecycle / Supply Chain" topic.

### INBOUND-LOCAL — Local entry points
An entry point callable by other software on the device or in the browser, without sender verification.
Control: every local entry surface — IPC, deep links, custom schemes, cross-window messaging — authenticates or validates the sender before acting (R5).
STRIDE: Spoofing. CWE: 926, 939, 346.
Refs: Cheat Sheet "Mobile Application Security" / platform hardening guides; ASVS mobile topics.

### EMBEDDED — Embedded untrusted content
Untrusted embedded content gains privileged host capabilities.
Control: embedded web content and plugins run with least privilege — no privileged bridges by default, origin checks on every bridge call (R4).
STRIDE: ElevationOfPrivilege. CWE: 749, 829, 346.
Refs: Cheat Sheet "Third Party Javascript Management"; ASVS "Software Integrity" / platform topics.

### RESOURCE — Resource consumption
Unbounded resource consumption.
Control: bound everything — request size, rate, concurrency, query cost, and timeouts — per caller identity. Findings need a concrete business-impact claim to survive validation (hard exclusions apply otherwise).
STRIDE: DoS. CWE: 400, 770, 1333, 799.
Refs: Cheat Sheets "Denial of Service", "REST Security" (rate limiting); OWASP API Security Top 10, Unrestricted Resource Consumption.

### ACCOUNTABILITY — Auditability
Security-relevant actions are not recorded, or are recorded forgeably.
Control: security-relevant actions are logged append-only with actor, action, target, and time, safe from injection and tampering. Usually informational (hard exclusion) unless forgery enables a concrete attack.
STRIDE: Repudiation. CWE: 778, 117, 223.
Refs: Cheat Sheet "Logging"; ASVS chapter "Error Handling and Logging".

## Editions of external lists

| List | Edition used | Where |
|---|---|---|
| OWASP Top 10 | 2025 (final, January 2026) | https://owasp.org/Top10/ |
| OWASP API Security Top 10 | 2023 | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ |
| OWASP Mobile Top 10 | 2024 (final release; content dir "2023-risks") | https://owasp.org/www-project-mobile-top-10/ |

When a new edition of any list ships, update `mappings.md` and this table together.

## config.json compatibility

`vulnerability_patterns.enabled` (the legacy list) stays honored for compatibility with existing repositories and evals. The new key is `catalog.disabled_classes` (default `[]`): the scan and the detectors check every applicable class except those listed — e.g. `"catalog": {"disabled_classes": ["RESOURCE", "ACCOUNTABILITY"]}` for a team that tracks those outside this skill.

When both exist, `catalog.disabled_classes` is authoritative; `vulnerability_patterns.enabled` is ignored for classes the catalog knows (it remains a hint for custom, non-catalog patterns).
