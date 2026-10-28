# Notice

Parts of this skill are adapted from
[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill),
licensed under the MIT License:

- the severity anchors (`SKILL.md`, Severity anchors);
- the invariant-based hunting method (`references/scouts.md`), adapted from
  its "Core hunting method" (`HUNTING.md`);
- the AI and LLM hunting classes (`references/ai-and-llm.md`), adapted from
  `AI-AND-LLM.md`, with verdict names changed to this skill's;
- the coverage model of `coverage.json` (`references/data-schema.md`) —
  unit ids derived from source references, carrying unchanged coverage
  between runs, the per-status state table, and validating coverage after
  every update — reimplemented after the ideas of its coverage ledger
  (`RECONNAISSANCE.md`, `validate-coverage-ledger.cjs`); no code was
  copied.

The adapted material was rewritten for this skill's pipeline and terms; the
original license follows.

---

MIT License

Copyright (c) 2025-2026 Cloudflare, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
