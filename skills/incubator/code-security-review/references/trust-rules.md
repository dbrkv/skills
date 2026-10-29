# Trust rules, exclusions, precedents

These rules decide what counts as exposed, what counts as attacker-controlled, and which findings are noise. The scan uses them for recall; the validators use them for verdicts. Copy this file in full into every validator.

**Order of precedence:** the project's own security guidelines, then the trust rules below, then the hard exclusions and precedents. A precedent survives only where no rule above it contradicts it.

## Trust rules

- **T1. What ships to a client is public.** Browser bundles, mobile apps, and public configuration are readable by anyone, including build-time variables inlined into them. The precedent "environment variables are trusted" applies only to values that stay on the server.
- **T2. Client-side checks are not a control.** Hiding a button or validating in the browser is UX. Access to a server resource is checked where the resource lives, on every entry point that reaches it.
- **T3. Framework protections cover only what goes through the framework.** Escaping, parameterization, CSRF tokens, and access rules protect the paths that use them. Code that bypasses the framework (raw queries, raw output, a route outside the access rules) is unprotected until shown otherwise.
- **T4. Each implementation is checked on its own.** When one contract has several implementations (adapters, drivers, platforms), a control in one does not extend to the others.
- **T5. Implicit coercion inside a security decision is suspicious.** Loose comparison, truthiness checks, and normalization before comparison (loose equality, case folding, Unicode normalization) can make different values equal.
- **T6. Controls outside the repository are unknown, not present.** Proxies, CDNs, WAFs, cloud policies, and platform settings are neither assumed to protect nor assumed to be missing. Reachability, though, follows from what the code serves: an HTTP server is reachable by network clients unless the repository proves otherwise (bound to localhost, a network policy in the repository) or the owner states it. A finding whose only deciding fact is such an external control (TLS termination, security headers, environment mode, disk encryption) is a hardening note in *Not checked*, not a finding.
- **T7. Harm to oneself is not a finding.** A user damaging only their own data within their own rights does not cross a trust boundary.
- **T8. Owner claims are assumptions.** "This is escaped elsewhere" or "that endpoint is internal" is checked in the code. If the code does not back it, the finding stays open and the report records the claim.

## Hard exclusions

Exclude these unless there is a concrete, demonstrable exploit path:

1. Denial of service without significant business impact
2. Secrets stored on disk with proper protection
3. Rate limiting concerns in general (informational). **Except:** missing limits on login, OTP or verification codes, password reset, and other credential or code guessing are findings; so is unlimited triggering of paid actions (SMS, email, external APIs).
4. Memory or CPU exhaustion without a clear attack path
5. Lack of input validation without a demonstrated impact
6. CI configuration issues without a specific untrusted-input path
7. Theoretical race conditions without a practical exploit. **Except:** races on money, bookings, balances, one-time tokens, and other state that must change exactly once are findings when two parallel requests can both pass the check.
8. Memory safety issues in memory-safe languages
9. Findings only in test files. **Except:** a real secret committed in a test file is still a committed secret.
10. Log injection or log spoofing
11. SSRF that controls only the path, not the host or protocol
12. Regular-expression DoS without demonstrated impact
13. Findings in documentation files
14. Missing audit logs in general (informational). **Except:** no trail at all for actions on money or permissions, where the threat model says one is required.

## Precedents

Trusted-by-default assumptions. When evidence shows one does not hold in a specific case, flag it.

- Environment variables and command-line flags are trusted, on the server only (T1).
- Random UUIDs (v4) are unguessable. Sequential IDs and time-based UUIDs are not.
- Template and UI frameworks that auto-escape output protect it, except where their raw-output escape hatch is used or escaping is turned off.
- Client-side code does not need its own authorization checks; the server does (T2).
- A user ID taken from a server-signed session or token is not attacker-controlled.
- Notebook files are rarely exploitable.
