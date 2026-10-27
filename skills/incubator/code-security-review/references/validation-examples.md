# Vulnerability validation examples (Phase 3)

This document provides few-shot examples for Phase 4 (validating a finding in an isolated context, with a refute-first mindset) and Phase 5 (PoC, CVSS, record verification). Outputs follow the response contract in `vulnerability-validation.md` exactly.

---

## Example 1: Confirmed SQL Injection

### Input finding

```json
{
  "id": "VULN-001",
  "severity": "HIGH",
  "vulnerability_type": "SQL Injection",
  "file": "src/api/users.js",
  "line_range": "45-49",
  "code_context": "const sql = `SELECT * FROM users WHERE name LIKE '%${query}%'`;"
}
```

### Refutation attempt

**1. Reachability** — traced from the entry point:

1. `GET /api/users` → `routes/users.js:12`
2. `usersRouter.get('/')` → `controllers/userController.js:28`
3. `searchUsers(req.query.search)` → `src/api/users.js:45` (vulnerable code)

Reachability: `EXTERNAL` — unauthenticated HTTP endpoint. No middleware runs before the handler.

**2. Control flow / attacker control** — source: `req.query.search` (HTTP query parameter) → passed directly to `searchUsers()` → interpolated into the SQL template literal → executed via `db.query(sql)`. No validation, encoding, or transformation anywhere on the path. Attacker control: FULL.

**3. Mitigations searched for and not found** — no input validation middleware on the route; raw SQL, not ORM parameterization; no WAF or SQLi protection. The threat model's "Existing Mitigations" for this threat lists none — verified against the code.

**4. Exploitability** — `EASY`: standard technique, browser or curl, no conditions.

**Refutation failed**: no validation, no framework protection, no unreachable branch. The path from attacker-controlled source to sink is complete.

### Validator response (Phase 4 contract)

```json
{
  "id": "VULN-001",
  "status": "CONFIRMED",
  "validated_severity": "CRITICAL",
  "confidence": "HIGH",
  "reachability": "EXTERNAL",
  "exploitability": "EASY",
  "exploitation_path": [
    "Attacker sends GET /api/users?search=<payload> (routes/users.js:12)",
    "Express passes req.query.search to searchUsers() unmodified (controllers/userController.js:28)",
    "searchUsers interpolates the input into the SQL template literal (src/api/users.js:45)",
    "db.query() executes the attacker's SQL (src/api/users.js:47)"
  ],
  "existing_mitigations": [],
  "reason": "Refutation failed: no validation, sanitization, or parameterization anywhere on the path from req.query.search to db.query(). Direct SQL interpolation with full attacker control; upgraded to CRITICAL because any unauthenticated caller can read the whole users table.",
  "evidence": [
    {"file": "routes/users.js", "line": 12, "note": "public route, no auth middleware"},
    {"file": "src/api/users.js", "line": 45, "note": "template literal interpolation of user input into SQL"},
    {"file": "src/api/users.js", "line": 47, "note": "raw db.query() execution, no parameterization"}
  ],
  "missing_fact": null
}
```

### Phase 5 (excerpt)

PoC (mandatory — CONFIRMED and CRITICAL):

```json
{
  "payload": "test%' OR '1'='1 --",
  "request": "GET /api/users?search=test%25'%20OR%20'1'%3D%271%20--",
  "expected_behavior": "Returns users with 'test' in name",
  "actual_behavior": "Returns ALL users in database"
}
```

PoC execution (default policy — execution disabled):

```json
"poc_executed": false,
"poc_result": null
```

CVSS — vector by the agent, score by the script:

```bash
python3 scripts/cvss-score.py "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"
# {"vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N", "score": 9.1, "version": "3.1"}
```

Record check: `{"decision": "verified"}` — file/lines exist, every exploitation_path step matches the code, the PoC's route and parameter exist, CRITICAL does not exceed the demonstrated impact (full table read).

---

## Example 2: False positive — sanitized input

### Input finding

```json
{
  "id": "VULN-002",
  "severity": "HIGH",
  "vulnerability_type": "SQL Injection",
  "file": "src/api/products.js",
  "line_range": "78-82",
  "code_context": "const sql = `SELECT * FROM products WHERE category = '${category}'`;"
}
```

### Refutation attempt

**1. Reachability** — `GET /api/products` → `routes/products.js:15` → **`validateRequest(categorySchema)` middleware runs FIRST** → `getProducts(req.query.category)` → `src/api/products.js:78`.

**2. Control flow** — source: `req.query.category` → validated by Joi schema at `middleware/validation.js:23`: `Joi.string().valid('electronics', 'clothing', 'food', 'other')` → only enum values pass → then interpolated into SQL.

**3. Mitigations found** — the enum validation admits exactly four literal strings; any payload with quotes, spaces, or SQL metacharacters fails with 400 before the handler runs.

**Refutation succeeded**: the input is restricted to four predefined values before reaching the vulnerable code.

### Validator response

```json
{
  "id": "VULN-002",
  "status": "FALSE_POSITIVE",
  "validated_severity": "MEDIUM",
  "confidence": "HIGH",
  "reachability": "EXTERNAL",
  "exploitability": "NOT_EXPLOITABLE",
  "exploitation_path": [],
  "existing_mitigations": ["Joi enum validation in middleware/validation.js:23, applied at routes/products.js:15 before the handler"],
  "reason": "Input is restricted to four enum values by Joi validation middleware that runs before the handler. No SQL metacharacters can reach the interpolation. Parameterized queries would still be better hygiene, hence MEDIUM severity for the finding record.",
  "evidence": [
    {"file": "middleware/validation.js", "line": 23, "note": "Joi.string().valid('electronics','clothing','food','other') — strict enum, rejects everything else with 400"},
    {"file": "routes/products.js", "line": 15, "note": "validateRequest(categorySchema) applied to the route before the handler"}
  ],
  "missing_fact": null
}
```

---

## Example 3: Confirmed XSS with framework bypass (MEDIUM)

### Input finding

```json
{
  "id": "VULN-003",
  "severity": "MEDIUM",
  "vulnerability_type": "XSS",
  "file": "src/components/UserProfile.jsx",
  "line_range": "34-36",
  "code_context": "<div dangerouslySetInnerHTML={{__html: user.bio}} />"
}
```

### Refutation attempt

**1. Reachability** — component rendered at `/profile/:userId`; profiles are public; `user.bio` is user-editable via profile settings.

**2. Control flow** — source: bio input in profile settings form → stored in `users.bio` → returned by `GET /api/users/:id` → rendered with `dangerouslySetInnerHTML`.

**3. Mitigations searched** — React auto-escaping is **explicitly bypassed** (`dangerouslySetInnerHTML`); no CSP headers configured; no server-side sanitization of bio. The "React is XSS-safe" precedent does not apply — it excludes exactly this API.

**4. Exploitability** — `EASY`: attacker sets bio to a script/img-onerror payload, victim views the public profile.

**Refutation failed**: the one framework protection that would apply is explicitly disabled.

### Validator response

```json
{
  "id": "VULN-003",
  "status": "CONFIRMED",
  "validated_severity": "MEDIUM",
  "confidence": "HIGH",
  "reachability": "EXTERNAL",
  "exploitability": "EASY",
  "exploitation_path": [
    "Attacker sets their profile bio to <img src=x onerror=...> via profile settings (no sanitization on the input)",
    "Payload stored in users.bio",
    "Victim visits the attacker's public profile /profile/:userId",
    "UserProfile.jsx renders bio with dangerouslySetInnerHTML (line 34), bypassing React escaping",
    "Script executes in the victim's browser"
  ],
  "existing_mitigations": [],
  "reason": "Stored XSS: attacker-controlled HTML reaches the DOM through dangerouslySetInnerHTML, which disables React's auto-escaping. No CSP, no server-side sanitization. MEDIUM: requires a victim visit and yields session theft, not server compromise.",
  "evidence": [
    {"file": "src/components/UserProfile.jsx", "line": 34, "note": "dangerouslySetInnerHTML with user.bio — explicit React escaping bypass"},
    {"file": "src/routes/profile.js", "line": 8, "note": "public profile route, no authentication required to view"}
  ],
  "missing_fact": null
}
```

### Phase 5 (excerpt)

PoC below severity HIGH is optional; included here because it sharpens the finding:

```json
"proof_of_concept": {
  "payload": "<img src=x onerror=\"alert('XSS')\">",
  "request": "PATCH /api/users/me with body {\"bio\": \"<img src=x onerror=\\\"alert('XSS')\\\">\"}",
  "expected_behavior": "Bio displayed as text or sanitized HTML",
  "actual_behavior": "JavaScript executes in victim's browser"
},
"poc_executed": false,
"poc_result": null
```

```bash
python3 scripts/cvss-score.py "CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N"
# {"vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N", "score": 6.1, "version": "3.1"}
```

---

## Example 4: NEEDS_MANUAL_REVIEW — missing fact

### Input finding

```json
{
  "id": "VULN-004",
  "severity": "HIGH",
  "vulnerability_type": "Command Injection",
  "file": "src/workers/imageProcessor.js",
  "line_range": "56-60",
  "code_context": "exec(`convert ${inputPath} -resize ${size} ${outputPath}`)"
}
```

### Refutation attempt

**1. Reachability** — worker code, not directly callable: triggered by messages on the `image-processing` queue; messages are published by the upload endpoint `POST /api/upload`. Indirect EXTERNAL.

**2. Control flow** — the message carries `{ inputPath, size, outputPath }`. The publisher (upload-service) is **a different service, outside this repository**. Whether `size` and `inputPath` are user-controlled and whether they are validated before publishing cannot be determined from this codebase.

**Refutation inconclusive**: the exec() sink is real and reachable indirectly, but the decisive fact about attacker control lives outside the repository. Exactly one specific fact is missing — this is NEEDS_MANUAL_REVIEW, not a parking place: name the fact.

### Validator response

```json
{
  "id": "VULN-004",
  "status": "NEEDS_MANUAL_REVIEW",
  "validated_severity": "HIGH",
  "confidence": "MEDIUM",
  "reachability": "EXTERNAL",
  "exploitability": "MEDIUM",
  "exploitation_path": [],
  "existing_mitigations": [],
  "reason": "exec() with interpolated queue-message fields is a real sink, reachable indirectly via POST /api/upload. Whether the interpolated values are attacker-controlled depends on the publisher (upload-service), which is outside this repository, so refutation cannot succeed or fail from source alone.",
  "evidence": [
    {"file": "src/workers/imageProcessor.js", "line": 56, "note": "exec() with interpolated inputPath/size/outputPath from queue message"},
    {"file": "src/routes/upload.js", "line": 30, "note": "publishes to image-processing queue; validation status of published fields not visible here"}
  ],
  "missing_fact": "Whether upload-service validates inputPath and size before publishing to the image-processing queue (publisher source is outside this repository)"
}
```

In the artifact this becomes a `needs_manual_review` entry with `reason_code: "missing_fact"`.

---

## Example 5: False positive — server-signed JWT input

### Input finding

```json
{
  "id": "VULN-005",
  "severity": "MEDIUM",
  "vulnerability_type": "SQL Injection",
  "file": "src/repositories/orderRepository.js",
  "line_range": "23-25",
  "code_context": "return db.query(`SELECT * FROM orders WHERE user_id = ${userId}`);"
}
```

### Refutation attempt

**1. Reachability** — `GET /api/orders`, behind JWT authentication middleware.

**2. Control flow** — `userId` is `req.user.id`, set by auth middleware from a **server-signed JWT**; the id is a UUID generated at registration. The attacker cannot modify their token payload without the signing secret.

**3. Mitigations found** — the "user id from a signed JWT is not attacker-controlled" precedent applies directly (verified: middleware/auth.js:15 verifies the signature before the route runs).

**Refutation succeeded**: the interpolated value is server-controlled.

### Validator response

```json
{
  "id": "VULN-005",
  "status": "FALSE_POSITIVE",
  "validated_severity": "LOW",
  "confidence": "HIGH",
  "reachability": "AUTHENTICATED",
  "exploitability": "NOT_EXPLOITABLE",
  "exploitation_path": [],
  "existing_mitigations": ["JWT signature verification in middleware/auth.js:15; userId is a server-generated UUID from the signed token"],
  "reason": "userId comes from req.user.id, set by auth middleware from a server-signed JWT. The value is not attacker-controlled without the signing secret. Parameterization would still be best practice, hence LOW.",
  "evidence": [
    {"file": "middleware/auth.js", "line": 15, "note": "jwt.verify() runs before the route; req.user.id comes from the signed payload"},
    {"file": "services/auth.js", "line": 45, "note": "id is a server-generated UUID assigned at registration"}
  ],
  "missing_fact": null
}
```

---

## Edge cases

### Invalid validator output

First response for VULN-006 arrives wrapped in prose and misses `evidence`. Do not repair it. Re-run once with a fresh agent. The second response is valid → use it. Had the second response also been invalid:

```json
{
  "id": "VULN-006",
  "reason_code": "validator_output_invalid",
  "reason": "validator returned contract-invalid output twice",
  "missing_fact": null,
  "evidence": []
}
```

### Validation budget

18 candidates, `validation.max_findings: 15`. The 15 highest by severity (then confidence) are validated; the 3 remainder:

```json
{
  "id": "VULN-016",
  "reason_code": "validation_budget",
  "reason": "not validated: 18 candidates exceeded the validation budget of 15",
  "missing_fact": null,
  "evidence": []
}
```

### Degraded (sequential) mode — honest marking

No subagents available: findings are validated one by one in the same context, and the record check is done by the same context. The artifact must say so:

```json
"validation_meta": {
  "validation_isolation": "sequential",
  "record_verification": "self"
}
```

…and `report.md` carries one header line: "Validation ran in sequential mode (no isolated validators); record verification was self-review."

### Anti-escalation on record verification

The verifier of VULN-007 (CONFIRMED MEDIUM) responds with `replace` and a record marked CONFIRMED HIGH. Applying it would upgrade the verdict — forbidden. The upgrade is discarded; the finding goes back to Phase 4 for full re-validation. A `replace` that only fixes `line_range` and rewords two `exploitation_path` steps (same status, same severity) applies directly and is re-verified once by a different fresh agent.

---

## Key takeaways

### The refute-first mindset

- You did not write the finding — hunt for the reason it is wrong before concluding it is right
- CONFIRMED requires a failed refutation AND a complete, code-anchored exploitation path
- NEEDS_MANUAL_REVIEW names exactly one decisive missing fact; it is not a doubt bucket
- FALSE_POSITIVE names the code that refutes the finding

### When to confirm

- Attacker can control input that reaches vulnerable code
- No sanitization or validation in the data flow
- Framework protections are bypassed or disabled
- Can construct a working proof-of-concept

### When to mark false positive

- Input is validated/sanitized before reaching vulnerable code
- Framework provides automatic protection that's enabled
- The "user input" is actually server-controlled (e.g., from a signed token)
- Code is unreachable from any entry point
- The finding matches a hard exclusion or precedent
