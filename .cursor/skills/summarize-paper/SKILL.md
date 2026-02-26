---
name: summarize-paper
description: Summarize computer science academic papers into structured Markdown using PDF MCP tools. Use when the user asks to summarize, distill, review, or read a CS/academic paper, or mentions reading a PDF paper.
---

# CS Paper Summarization

Distill a CS paper into a concise, mechanism-focused Markdown summary. The source PDF can be anywhere on disk — the agent reads it via its absolute or relative path. Output is always saved to `Summaries/<pdf_filename>_summary.md` inside the project root.

## Tools & Constraints

- Use ONLY the PDF MCP tools. Call `pdf_info` first.
- Prefer `pdf_read_section`; fall back to `pdf_read_pages` only when it returns empty.
- Do NOT read References, Related Work, or Appendix unless a core mechanism is missing from main sections.
- If information cannot be found, state: "Not explicitly specified."

## Phase 1: Profile (internal — do NOT output)

Read **only** Abstract + Introduction (+ Conclusion if needed). Then determine:

1. **Paper type** — use structural signals, not keywords:
   - *Learning*: trainable parameters, loss minimization, training loop, inference procedure, dataset/benchmark.
   - *Physics*: state evolution, governing equations/constraints/energy, solver/linear system, time integration/stability.
   - *Hybrid*: both Learning and Physics are central.
   - *General*: none of the above dominate (e.g., rendering, geometry processing, HCI, systems, PL). Use this when the paper's core contribution does not revolve around a training loop or a physics solver.
2. **Sections to read** — list the method/technical sections from the TOC that must be read in Phase 2.
3. **Search queries** — 3-5 short strings for `pdf_search` to locate key details (e.g., "Algorithm", "loss", "dataset", "solver", "convergence").

## Phase 2: Write

1. Read only the sections identified in Phase 1. Use `pdf_search` with the queries from Phase 1.
2. Follow [template.md](template.md) exactly. Include only the mechanism blocks matching the paper type. For *General* papers, invent domain-appropriate blocks that parallel the structure and granularity of the Learning/Physics blocks (see template for guidance).
3. For the logical flow, map every paper to: **Problem → Bottleneck → Mechanism → Steps → Evidence → Boundary**.

## Style

**Intuitive first, formal second** — every section (except Results) should read like explaining the paper to a smart colleague, not like paraphrasing the abstract:

- Lead with *why* something is needed or *why* it works, then give the formal name/equation.
- Use analogies, concrete mental images, and cause-effect reasoning (e.g. "triangular solves are sequential because each row depends on the previous — that kills GPU parallelism" rather than "triangular solves are poorly parallelizable").
- The **High-Level Idea** is the single most important paragraph: the reader should think "ah, I get it" before seeing any math.
- Rephrase jargon in plain words first, formal name in parentheses after.
- Keep each bullet to **one core idea**. If a bullet needs two sentences, split it or cut.
- **Exception: Results (Section 5).** Rigorous only — exact numbers, metrics, comparisons as stated. No analogies.

**Conciseness:**

- For long derivations: state start + result, then `*(see Section X)*`.
- Only include equations that appear in "How it works" or Pseudocode.
- For theorems/proofs: one-sentence claim; skip proof.

## Output Rules

- Append `*(Source: Section X Title)*` after each item/bullet.
- Hard limit: **680 words** (excluding pseudocode/algorithm block). Aim for the length in [example.md](example.md).
- **Save output using the `save_summary` MCP tool.** Pass the source PDF path and the full Markdown content. The tool derives the filename (`<pdf_stem>_summary.md`), creates `Summaries/` if needed, and writes the file. Do NOT use any other method to write the summary.
- **After saving, call the `convert_md_to_pdf` MCP tool** with the path returned by `save_summary`. This produces a matching PDF in the same directory (`Summaries/<pdf_stem>_summary.pdf`). Both files share the same base name — only the extension differs.
