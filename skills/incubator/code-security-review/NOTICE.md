# Notice

This skill adapts material from the following projects.

## Factory-AI/skills

<https://github.com/Factory-AI/skills>, MIT License, Copyright (c) 2025.

The structure of this skill (a persistent STRIDE threat model, a scan, and a validation phase), the threat model template, and the STRIDE checklists started as an adaptation of the `threat-model-generation`, `commit-security-scan`, `vulnerability-validation`, and `security-review` skills. They have since been reworked: the skill is harness-neutral, keeps no JSON artifacts, validates each finding with an isolated refuter, and never executes the target.

## anthropics/claude-code-security-review

<https://github.com/anthropics/claude-code-security-review>, MIT License, Copyright (c) 2025 Anthropic.

The hard exclusions and precedents in `references/trust-rules.md` follow the false-positive filtering rules of that project, with carve-outs added for credential guessing, paid actions, and races on state that must change exactly once.

## MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
