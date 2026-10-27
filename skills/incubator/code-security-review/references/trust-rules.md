# Trust rules, exclusions, precedents

The trust rules shape both ends of the pipeline: scouts apply them for recall
(what counts as exposed), verifiers apply them to verdicts. **On conflict, a
rule wins over a precedent or a hard exclusion; a precedent survives only
where no rule contradicts it.**

## Trust rules R1–R10

- **R1.** Everything shipped to a client — web bundle, binary, application
  package, public configuration — is public, including configuration values
  and build-time variables. The "environment variables are trusted" precedent
  applies only to values that stay on the server.
- **R2.** Data on a device or in a client is an asset. Its protection is
  determined by who else can read it (other applications, backups, the device
  owner with elevated rights, third-party scripts on the page) — not by the
  fact that "it's on the client".
- **R3.** Client-side checks are not a control for server resources. Access
  is verified where the resource lives.
- **R4.** Untrusted content that has access to privileged host capabilities
  (embedded web content, plugins, third-party scripts) is checked for origin
  at every call, not once at load time.
- **R5.** Entry points that other software on the same device or in the same
  browser can call (inter-process calls, link and scheme handlers,
  cross-window messaging) are treated as unauthenticated until the code proves
  otherwise.
- **R6.** Framework protections (escaping, parameterization, CSRF tokens)
  apply only to paths that go through the framework. Code that bypasses the
  framework is unprotected until proven otherwise.
- **R7.** When one contract has multiple implementations (platforms, adapters,
  drivers), each is checked separately; a control present in one does not
  extend to the others.
- **R8.** Comparisons that rely on implicit type coercion or normalization
  inside a security decision are suspicious.
- **R9.** Controls outside the repository (proxies, CDNs, cloud policies,
  platform settings) are neither present nor absent. If the deciding fact lies
  outside the repository, the verdict is needs_review naming that fact.
- **R10.** Self-harm — a user damaging only themselves within their own
  rights — is not a trust-boundary crossing and not a finding.

## Hard exclusions

Automatically exclude unless a concrete, demonstrable exploit path exists:

1. Denial of service without significant business impact
2. Secrets stored on disk if properly secured
3. Rate limiting concerns (informational only)
4. Memory/CPU exhaustion without a clear attack path
5. Lack of input validation without proven impact
6. GitHub Action / CI vulnerabilities without a specific untrusted-input path
7. Theoretical race conditions without a practical exploit
8. Memory safety issues in memory-safe languages (Rust, Go)
9. Findings only in test files — **except hardcoded secrets and leaked
   credentials**: a secret committed in a test file is still a committed
   secret; the SECRETS class applies in full
10. Log injection/spoofing concerns
11. SSRF that only controls the path (not host or protocol)
12. ReDoS without demonstrated impact
13. Findings in documentation files
14. Missing audit logs (informational only)

User-controlled content in AI prompts is not on this list: LLM-backed code is
hunted through `references/ai-and-llm.md`, whose discipline — prompt injection
alone is not a finding; a code-level boundary failure is required — replaces
the blanket exclusion.

## Precedents

Trusted-by-default assumptions that reduce false positives but are not
absolute — when evidence shows one does not hold, flag it:

- Environment variables and CLI flags are trusted (server-side only — see R1)
- UUIDs are unguessable
- React/Angular are XSS-safe unless using `dangerouslySetInnerHTML` or
  `bypassSecurityTrustHtml`
- Client-side code doesn't need auth checks (the server's responsibility — R3)
- Most notebook findings are not exploitable
- A user id extracted from a server-signed JWT is not attacker-controlled
