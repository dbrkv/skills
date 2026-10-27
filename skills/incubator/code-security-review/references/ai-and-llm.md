# AI and LLM hunting classes

*Verdicts use this skill's names (confirmed / likely / needs_review /
rejected); analysis is source-level only.*

#### When to use this file

Reach for this file when a language model participates in a trust-sensitive
decision: chatbots and assistants, RAG pipelines, persistent agent memory,
agent/tool-calling loops, MCP servers and clients, code that builds prompts
from untrusted input, or code that consumes model output and acts on it. The
important data flow is *untrusted content → model or memory → capability,
authority, or sink*.

Use this alongside `threat-classes.md`, not instead of it. Transport, access
control, query construction, filesystem use, and output rendering remain
ordinary trust boundaries; this file covers the model-specific delegation
layer.

## Core discipline (include in every scout and verifier prompt for this domain)

- Prompt injection alone is not a finding. Require a code-level boundary
  failure: content reaches another principal's context, invokes authority the
  requester lacks, discloses data they cannot read, or drives a sink they
  cannot reach directly.
- Model output, memory, tool descriptions, and MCP responses are untrusted
  inputs. Point to the code that grants authority, trusts output, writes
  durable state, or feeds a sink.
- A guardrail prompt is not a security boundary. Count only deterministic
  checks, resource-scoped authorization, isolation, binding, and constrained
  credentials.
- State the attacker, affected principal, effective execution identity,
  resource, exact action, authority used, and observable impact. An
  intentional direct request to use the requester's existing authority is not
  a delegation defect merely because a model executes it.
- Authorization and action binding are separate controls.
  Attacker-controlled content that causes an action under an affected
  principal's valid authority is an action-binding failure when that
  principal did not intentionally request or approve the exact action.

## Attack classes

### Context, retrieval, and memory

**Indirect injection through retrieved or ingested content** — an attacker
writes a RAG document, indexed page, file, email, issue body, tool response,
or metadata that enters a different principal's model context. Trace who can
write each source, how retrieval scopes it, whose session consumes it, and
what capability is enabled there. The defect is a missing deterministic
control, not persuasive text.

**Cross-session or cross-tenant context bleed** — history, embeddings,
retrieval results, or prompt caches keyed too broadly. Verify tenant and ACL
filters in the query itself and in every cache key.

**Persistent memory poisoning** — attacker-controlled content or model
summaries written into memory that later shapes another task, user, or
privileged session. Review who may write memory, its provenance and scope,
and whether retrieval distinguishes user preferences from tool policy.

**Prompt role and provenance confusion** — prompt assembly lets untrusted
text impersonate a system message, prior turn, tool result, or policy.
Confirm the forged provenance changes a deterministic trust decision or
reaches a meaningful capability.

### Tool and action

**Tool-argument injection into a downstream sink** — model-produced arguments
reach SQL, shell, file, URL-fetch, or privileged APIs without handler-side
validation. Structured output narrows shape; it does not establish
authorization or safe paths.

**Excessive agency and confused-deputy authority** — the agent uses a broad
service identity while the tool handler does not re-check the requesting
principal's permission on the named resource.

**Action-confirmation and approval binding** — a user approves one described
action, but execution can use changed arguments, a different resource, a
different principal, or a later model turn. Check retries and resumed
sessions: an approval must not authorize a mutated or duplicate side effect.

**Tool-schema and dispatcher disagreement** — the schema accepts aliases,
extra fields, duplicate keys, coercions, or out-of-range values that the
dispatcher or handler interprets differently. Compare the validated object
with the handler's object.

**Unbounded delegated action loops** — a bounded request enqueues repeated
spend, send, or mutation work without per-request budget, per-action
authorization, cancellation, or idempotency.

### MCP and sub-agent trust

**Trust inheritance** — a delegated task receives the full session,
credentials, memory, or capabilities rather than the least authority
required; delegated results are trusted on return.

**Server and tool identity confusion** — calls or results routed by
attacker-influenceable server names, tool names, request ids, or aliases
rather than the authenticated connection and outstanding request.

**Metadata as policy** — tool descriptions, resource metadata, prompts, or
schemas supplied by an MCP peer are trusted as authorization. Metadata can
guide the model; it cannot grant capability — find the deterministic
allowlist and handler authorization that stay authoritative.

### Output and disclosure

**Insecure output rendering** — model output reaches an executing HTML,
Markdown, template, URL, or command sink without the sink's required
encoding and policy.

**Sensitive context extraction** — the assembled context contains
credentials, another user's data, or access-granting policy values, and
user-influenced output exposes them.

## Universal moves

- Draw four maps first: each execution identity, each capability, every
  writable context or memory source, and each output destination. Connect
  the principal at the start to the authority at the end.
- Start at side-effecting tools and work backward through dispatcher,
  schema, confirmation, model context, retrieval, and ingestion.
- Compare direct, queued, retry, resume, batch, and delegated paths for the
  same action. The strongest gate must apply after arguments are final and
  before every side effect.

## Validation rules (before reporting any finding here)

1. Name the crossed boundary and the observable result: attacker, affected
   principal or shared resource, execution identity, target, and the
   unauthorized or unrequested action or disclosure.
2. For confused-deputy claims, prove the tool lacks requester-and-resource
   authorization and that the attacker cannot perform the same action
   normally. For action-binding claims, prove attacker-controlled content
   caused an action under the affected principal's authority that they did
   not intentionally request or approve.
3. For memory or retrieval claims, cite both the attacker-controlled write
   and the later cross-principal read or privileged decision. A shared
   record without a reachable consumer is not enough.
4. For schema disagreement, compare the normalized validated object with the
   handler's object.
5. For MCP identity claims, verify the authenticated connection, request
   correlation, and effective credential; when external server identity or
   deployment routing is required, the verdict is needs_review.
6. confirmed requires a complete source trace and a meaningful result;
   needs_review states the exact unresolved fact.
