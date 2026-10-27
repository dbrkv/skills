# Threat classes

The taxonomy scouts walk and verifiers reason with. Each class: the threat in
one phrase, the control essence (what "fixed" looks like — the refuter's
map), CWE anchors, and the default STRIDE. Findings carry `threat_class` +
`cwe`. STRIDE tokens: `Spoofing`, `Tampering`, `Repudiation`,
`InfoDisclosure`, `DoS`, `ElevationOfPrivilege`.

LLM/agent-backed targets additionally use `references/ai-and-llm.md`
alongside these classes.

## Overview

| ID | Threat | STRIDE | CWE anchors |
|---|---|---|---|
| INJ | Untrusted data interpreted as code, query, command, markup, or path | Tampering | 74; 89, 78, 79, 94, 943, 1336, 22, 611, 1321 |
| OUTBOUND | Server requests an attacker-controlled address | ElevationOfPrivilege | 918 |
| INTEGRITY | Data or code accepted without authenticity verification | Tampering | 502, 345, 494, 347 |
| AUTHN | Actor's identity not established, or weakly | Spoofing | 287, 306, 307, 640 |
| SESSION | Session or token forgeable, stealable, or non-expiring | Spoofing | 384, 613, 1004, 614 |
| AUTHZ-OBJ | Another's object via a controllable identifier | ElevationOfPrivilege ¹ | 639, 862 |
| AUTHZ-FUNC | Function or role above one's rights | ElevationOfPrivilege | 862, 863, 269 |
| AUTHZ-PROP | Object properties above one's rights (mass assignment, extra fields) | ElevationOfPrivilege ¹ | 915, 213 |
| LOGIC | Business-process invariants violated | Tampering | 840, 362 |
| SECRETS | Secrets in code, history, or shipped artifacts | InfoDisclosure | 798, 540 |
| DATA-AT-REST | Sensitive data readable by the unentitled | InfoDisclosure | 312, 922 |
| CRYPTO | Weak or misapplied crypto, unprotected transport, wrong cert verification | InfoDisclosure | 327, 326, 330, 319, 295 |
| CONFIG | Insecure configuration in the repository | InfoDisclosure | 942, 489, 1021 |
| EXPOSURE | Sensitive data in responses, errors, logs | InfoDisclosure | 200, 209, 532 |
| EXCEPTIONAL | Error path fails open or inconsistent | ElevationOfPrivilege | 755, 636 |
| SUPPLY | Vulnerable or unsupported dependencies | — ² | 1395, 1104 |
| INBOUND-LOCAL | Local entry without sender verification | Spoofing | 926, 939, 346 |
| EMBEDDED | Untrusted embedded content gains host capabilities | ElevationOfPrivilege | 749, 829, 346 |
| RESOURCE | Unbounded resource consumption | DoS | 400, 770, 1333, 799 |
| ACCOUNTABILITY | Security actions unrecorded or forgeably recorded | Repudiation | 778, 117, 223 |

¹ Override to InfoDisclosure when only reading is demonstrated (record why).
² SUPPLY applies only when the user supplies an advisory list — no scanners
run (SKILL.md hard rules).

## Applicability

Always on: INJ, OUTBOUND, INTEGRITY, AUTHN, SESSION, AUTHZ-OBJ, AUTHZ-FUNC,
AUTHZ-PROP, LOGIC, SECRETS, DATA-AT-REST, CRYPTO, CONFIG, EXPOSURE,
EXCEPTIONAL, RESOURCE, ACCOUNTABILITY. INBOUND-LOCAL and EMBEDDED — when
local entry surfaces (deep links, custom schemes, IPC, cross-window
messaging) or embedded content with host bridges exist. Under R1/R2, SECRETS
and DATA-AT-REST apply with full force to anything shipped to a client or
stored on a device — "it's just client config" is not a control.

## Class entries

### INJ — Injection
Untrusted data is interpreted as code, a query, a command, markup, or a path:
SQL and command injection, XSS, path traversal, XXE, expression/template
injection, prototype pollution.
Control: separation of data and code — parameterized queries, context-aware
output encoding, argv lists without a shell, resolved and rooted paths; not
blacklisting dangerous characters.

### OUTBOUND — Server-side request forgery
The server performs a request to an address the attacker controls.
Control: the server decides where it connects — allowlists of hosts and
schemes, no raw user-supplied URLs, normalization before any network call.

### INTEGRITY — Unverified data or code
Native deserialization of untrusted bytes, unsigned updates or plugins,
unverified signatures or webhooks.
Control: verify provenance before trusting — pinned signatures, checksums,
safe data formats; never deserialize untrusted bytes natively.

### AUTHN — Authentication
Missing or weak authentication, brute-forceable logins, weak reset flows.
Control: prove who is acting before anything else — strong authenticators, no
default or anonymous paths on sensitive operations, errors that don't leak
which factor failed.

### SESSION — Session management
Fixation, theft, non-expiration; insecure cookies; JWT none-algorithm or weak
secrets.
Control: sessions are bearer credentials — unpredictable, bound to the owner,
expiring, revocable server-side, rotated on privilege change.

### AUTHZ-OBJ — Object-level authorization (IDOR)
Access to someone else's object through a controllable identifier.
Control: every object access verifies the caller's relationship to that
object at the data-access point, not in the client.

### AUTHZ-FUNC — Function-level authorization
Missing authorization checks, role bypass, privilege escalation, RBAC escape.
Control: every privileged function checks the caller's right at the
server-side enforcement point, regardless of what the UI hides.

### AUTHZ-PROP — Property-level authorization
Mass assignment (blind request-body → model binding), extra sensitive fields
in responses.
Control: field allowlists for input binding and output shaping; never pass a
body straight through to a model or serializer.

### LOGIC — Business logic
Step-order violations, negative quantities or prices, limit bypass, races on
multi-step flows.
Control: server-side state machines for step order, server-computed prices
and limits, idempotency and locking for concurrent flows.

### SECRETS — Hardcoded secrets
Secrets in code, history, or shipped artifacts — including client bundles and
build-time variables (R1), and including test files (the exception to hard
exclusion 9).
Control: secrets live in a secrets manager or server-only configuration;
never in code, history, or anything shipped.

### DATA-AT-REST — Stored data
Sensitive data stored unencrypted where unentitled readers exist — on
devices, other applications and backups count as readers (R2).
Control: encrypt or permission-scope so only entitled components can read it.

### CRYPTO — Cryptography
Weak or broken algorithms, homemade crypto, cleartext transport, disabled
certificate verification.
Control: vetted primitives and protocols with library defaults; TLS
everywhere data moves.

### CONFIG — Configuration
Permissive CORS, debug flags, insecure policies in the repository.
Control: repository configuration is the most permissive artifact the
attacker gets — least privilege by default; a control that may live outside
the repo follows R9.

### EXPOSURE — Information exposure
Stack traces to clients, internal identifiers, sensitive fields in logs or
responses.
Control: the minimum necessary in responses, errors, and logs.

### EXCEPTIONAL — Mishandled exceptions
Error paths that fail open, skip authorization cleanup, or leave inconsistent
state.
Control: fail closed — deny, clean up, leave consistent state.

### SUPPLY — Dependencies
Vulnerable or unsupported dependencies. No scanners run; when the user
supplies advisories, check the installed versions and the reachability of the
vulnerable APIs from the code.

### INBOUND-LOCAL — Local entry points
Deep links, custom schemes, IPC handlers, cross-window messages without
sender verification (R5).
Control: every local entry surface authenticates or validates the sender
before acting.

### EMBEDDED — Embedded untrusted content
WebViews, plugins, or third-party scripts with privileged bridges, origin
checked at most once (R4).
Control: least privilege — no privileged bridges by default, origin checks on
every bridge call.

### RESOURCE — Resource consumption
Missing rate limits, unbounded uploads or queries, algorithmic complexity,
missing pagination. Needs a concrete business-impact claim to survive
(exclusions 1 and 4).
Control: bound request size, rate, concurrency, query cost, and timeouts —
per caller identity.

### ACCOUNTABILITY — Auditability
Missing audit logging, forgeable trails, log injection. Usually informational
(exclusions 10 and 14) unless forgery enables a concrete attack.
Control: append-only logs with actor, action, target, and time.
