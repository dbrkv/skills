# CWE → OWASP category mappings

Used **only when rendering `report.md`** — the OWASP category of a finding is computed at report time and is never stored in any artifact. This file pins the edition of each list and the exact rows; rows are taken from the official category pages, not from memory.

Rules:

- Take the category from the table for the finding's CWE. A CWE absent from the table renders as `unmapped` — never guess a category.
- Primary table: OWASP Top 10:2025 (final, January 2026), for all findings.
- Secondary, when they say more than the primary:
  - **API Security Top 10:2023** — for findings located in API handlers (routes/endpoints). Note the provenance caveat below.
  - **Mobile Top 10:2024** — for findings on the `device-package` boundary (mobile/desktop applications). Class-level associations only (this edition publishes no per-CWE mapping).

## Top 10:2025 (CWE → category)

Source: the "List Of Mapped CWEs" section of each official category page under https://owasp.org/Top10/2025/. Only the catalog's CWE anchors are listed; the full per-category lists live on the pages.

| CWE | Category | Catalog classes using this anchor |
|---|---|---|
| CWE-22 | A01:2025 Broken Access Control | INJ |
| CWE-74 | A05:2025 Injection | INJ |
| CWE-78 | A05:2025 Injection | INJ |
| CWE-79 | A05:2025 Injection | INJ |
| CWE-89 | A05:2025 Injection | INJ |
| CWE-94 | A05:2025 Injection | INJ |
| CWE-117 | A09:2025 Security Logging and Alerting Failures | ACCOUNTABILITY |
| CWE-200 | A01:2025 Broken Access Control | EXPOSURE |
| CWE-209 | A10:2025 Mishandling of Exceptional Conditions | EXPOSURE |
| CWE-213 | unmapped (see API table) | AUTHZ-PROP |
| CWE-223 | A09:2025 Security Logging and Alerting Failures | ACCOUNTABILITY |
| CWE-269 | A06:2025 Insecure Design | AUTHZ-FUNC |
| CWE-287 | A07:2025 Authentication Failures | AUTHN |
| CWE-295 | A07:2025 Authentication Failures | CRYPTO |
| CWE-306 | A07:2025 Authentication Failures | AUTHN |
| CWE-307 | A07:2025 Authentication Failures | AUTHN |
| CWE-312 | A06:2025 Insecure Design | DATA-AT-REST |
| CWE-319 | A04:2025 Cryptographic Failures | CRYPTO |
| CWE-326 | A04:2025 Cryptographic Failures | CRYPTO |
| CWE-327 | A04:2025 Cryptographic Failures | CRYPTO |
| CWE-330 | A04:2025 Cryptographic Failures | CRYPTO |
| CWE-346 | A07:2025 Authentication Failures | INBOUND-LOCAL, EMBEDDED |
| CWE-347 | A04:2025 Cryptographic Failures | INTEGRITY |
| CWE-345 | A08:2025 Software or Data Integrity Failures | INTEGRITY |
| CWE-362 | A06:2025 Insecure Design | LOGIC |
| CWE-384 | A07:2025 Authentication Failures | SESSION |
| CWE-400 | unmapped (see API table) | RESOURCE |
| CWE-489 | A02:2025 Security Misconfiguration | CONFIG |
| CWE-494 | A08:2025 Software or Data Integrity Failures | INTEGRITY |
| CWE-502 | A08:2025 Software or Data Integrity Failures | INTEGRITY |
| CWE-532 | A09:2025 Security Logging and Alerting Failures | EXPOSURE |
| CWE-540 | A01:2025 Broken Access Control | SECRETS |
| CWE-611 | A02:2025 Security Misconfiguration | INJ |
| CWE-613 | A07:2025 Authentication Failures | SESSION |
| CWE-614 | A02:2025 Security Misconfiguration | SESSION |
| CWE-636 | A10:2025 Mishandling of Exceptional Conditions | EXCEPTIONAL |
| CWE-639 | A01:2025 Broken Access Control | AUTHZ-OBJ |
| CWE-640 | A07:2025 Authentication Failures | AUTHN |
| CWE-749 | unmapped | EMBEDDED |
| CWE-755 | A10:2025 Mishandling of Exceptional Conditions | EXCEPTIONAL |
| CWE-770 | unmapped (see API table) | RESOURCE |
| CWE-778 | A09:2025 Security Logging and Alerting Failures | ACCOUNTABILITY |
| CWE-798 | A07:2025 Authentication Failures | SECRETS |
| CWE-799 | A06:2025 Insecure Design | RESOURCE |
| CWE-829 | A08:2025 Software or Data Integrity Failures | EMBEDDED |
| CWE-840 | unmapped | LOGIC |
| CWE-862 | A01:2025 Broken Access Control | AUTHZ-OBJ, AUTHZ-FUNC |
| CWE-863 | A01:2025 Broken Access Control | AUTHZ-FUNC |
| CWE-915 | A08:2025 Software or Data Integrity Failures | AUTHZ-PROP |
| CWE-918 | A01:2025 Broken Access Control | OUTBOUND |
| CWE-922 | A01:2025 Broken Access Control | DATA-AT-REST |
| CWE-926 | A08:2025 Software or Data Integrity Failures | INBOUND-LOCAL |
| CWE-939 | unmapped | INBOUND-LOCAL |
| CWE-942 | A02:2025 Security Misconfiguration | CONFIG |
| CWE-943 | unmapped | INJ |
| CWE-1004 | A02:2025 Security Misconfiguration | SESSION |
| CWE-1021 | A06:2025 Insecure Design | CONFIG |
| CWE-1104 | A03:2025 Software Supply Chain Failures | SUPPLY |
| CWE-1321 | unmapped | INJ |
| CWE-1333 | unmapped | RESOURCE |
| CWE-1336 | unmapped | INJ |
| CWE-1395 | A03:2025 Software Supply Chain Failures | SUPPLY |

**2025 edition shifts worth knowing when a report reader expects 2021 numbering:** CWE-22 (path traversal) now sits under A01 Broken Access Control; CWE-611 (XXE) under A02 Security Misconfiguration; CWE-269 (privilege escalation) under A06 Insecure Design; CWE-915 (mass assignment) under A08 Software or Data Integrity Failures; CWE-798 (hardcoded credentials) under A07 Authentication Failures; CWE-209 (error information exposure) under A10 Mishandling of Exceptional Conditions.

## API Security Top 10:2023 (secondary, for API-handler findings)

Provenance caveat: this edition does not publish a formal "mapped CWEs" list per category. The rows below are the **CWEs explicitly named on the official 2023 category pages** (https://owasp.org/API-Security/editions/2023/en/0x11-t10/). Use them only for findings located in API handlers, and only where they add precision over the Top 10:2025 column — notably for CWEs that are `unmapped` there.

| CWE | API category (official page names this CWE) |
|---|---|
| CWE-200 | API10:2023 Unsafe Consumption of APIs |
| CWE-204 | API2:2023 Broken Authentication |
| CWE-213 | API3:2023 Broken Object Property Level Authorization |
| CWE-285 | API1:2023 Broken Object Level Authorization; API5:2023 Broken Function Level Authorization |
| CWE-307 | API2:2023 Broken Authentication |
| CWE-319 | API8:2023 Security Misconfiguration; API10:2023 Unsafe Consumption of APIs |
| CWE-400 | API4:2023 Unrestricted Resource Consumption |
| CWE-639 | API1:2023 Broken Object Level Authorization |
| CWE-770 | API4:2023 Unrestricted Resource Consumption |
| CWE-799 | API4:2023 Unrestricted Resource Consumption |
| CWE-915 | API3:2023 Broken Object Property Level Authorization |
| CWE-918 | API7:2023 Server Side Request Forgery |
| CWE-942 | API8:2023 Security Misconfiguration |

## Mobile Top 10:2024 (secondary, for `device-package` boundary findings)

Provenance caveat: this edition (final release 2024; content at https://owasp.org/www-project-mobile-top-10/) publishes **no per-CWE mappings**. The associations below are **class-level, by category definition** — do not present them as official CWE mappings. Render the category alongside the Top 10:2025 column, with "per Mobile Top 10:2024 definition".

| Catalog class | Mobile Top 10:2024 category (by definition) |
|---|---|
| AUTHN, SESSION | M3 Insecure Authentication/Authorization |
| SECRETS | M1 Improper Credential Usage |
| SUPPLY | M2 Inadequate Supply Chain Security |
| AUTHZ-OBJ, AUTHZ-FUNC, AUTHZ-PROP | M3 Insecure Authentication/Authorization |
| INJ | M4 Insufficient Input/Output Validation |
| CRYPTO (transport) | M5 Insecure Communication |
| EXPOSURE, DATA-AT-REST (privacy angle) | M6 Inadequate Privacy Controls |
| CONFIG (build/flags) | M7 Insufficient Binary Protection; M8 Security Misconfiguration |
| DATA-AT-REST | M9 Insecure Data Storage |
| CRYPTO (at rest) | M10 Insufficient Cryptography |

## Maintenance

When a new edition of any list ships:

1. Re-fetch the official category pages; rebuild the affected table from the "List Of Mapped CWEs" sections (Top 10) or the CWEs named on the pages (API).
2. Update the "Editions of external lists" table in `threat-catalog.md` in the same change.
3. Move CWEs that became mapped/unmapped accordingly; `unmapped` is a state, not an error.
