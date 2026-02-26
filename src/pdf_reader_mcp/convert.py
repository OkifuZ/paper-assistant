"""Markdown-to-PDF conversion with KaTeX math rendering."""

import re
from pathlib import Path

from .app import mcp

# ---------------------------------------------------------------------------
# Math-safe Markdown → HTML helpers
# ---------------------------------------------------------------------------

_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.DOTALL)
_PLACEHOLDER_RE = re.compile(r"MATHPH(\d+)ENDMATH")


def _extract_math(text: str) -> tuple[str, list[tuple[str, bool]]]:
    """Replace $...$ / $$...$$ with safe placeholders before markdown parsing.

    Returns the modified text and a list of (expression, is_display) tuples.
    """
    expressions: list[tuple[str, bool]] = []

    def _replacer(m: re.Match) -> str:
        display = m.group(1)
        inline = m.group(2)
        expr = display if display is not None else inline
        idx = len(expressions)
        expressions.append((expr, display is not None))
        return f"MATHPH{idx}ENDMATH"

    return _MATH_RE.sub(_replacer, text), expressions


def _restore_math_delimiters(
    html: str, expressions: list[tuple[str, bool]],
) -> str:
    """Replace MATHPH...ENDMATH placeholders back to $...$ / $$...$$ delimiters."""

    def _replacer(m: re.Match) -> str:
        idx = int(m.group(1))
        if idx >= len(expressions):
            return m.group(0)
        expr, is_display = expressions[idx]
        return f"$${expr}$$" if is_display else f"${expr}$"

    return _PLACEHOLDER_RE.sub(_replacer, html)


# ---------------------------------------------------------------------------
# KaTeX HTML wrapper + page CSS
# ---------------------------------------------------------------------------

_KATEX_VERSION = "0.16.21"

_PAGE_CSS = """\
body {
    font-family: "Georgia", "Times New Roman", "Noto Serif", serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #222;
    text-align: justify;
    hyphens: auto;
    padding: 0;
}
p {
    margin: 0 0 2pt;
    text-indent: 1.5em;
}
h1 + p, h2 + p, h3 + p, hr + p, blockquote > p:first-child, li > p:first-child {
    text-indent: 0;
}
h1, h2, h3 {
    font-family: "Georgia", "Times New Roman", "Noto Serif", serif;
}
h1 {
    text-align: center;
    font-size: 17pt;
    margin: 0 0 12pt;
}
h2 {
    font-size: 13pt;
    font-weight: bold;
    margin: 14pt 0 4pt;
}
h3 {
    font-size: 11pt;
    margin: 10pt 0 3pt;
}
code {
    font-family: "Consolas", "Liberation Mono", monospace;
    font-size: 9pt;
    background: #f5f5f5;
    padding: 0.5pt 2pt;
}
pre {
    font-family: "Consolas", "Liberation Mono", monospace;
    font-size: 9pt;
    background: #fafafa;
    border: 0.5pt solid #ddd;
    padding: 6pt;
    overflow-x: auto;
}
pre code { background: none; padding: 0; }
blockquote {
    margin: 4pt 0 4pt 18pt;
    padding: 0;
    border: none;
    font-style: italic;
    color: #333;
}
ul, ol {
    padding-left: 1.5em;
    margin: 3pt 0;
}
ol {
    padding-left: 1.2em;
    font-style: normal;
}
ol > li::marker {
    font-family: "Helvetica Neue", "Arial", sans-serif;
    font-weight: 600;
    font-size: 0.9em;
}
li { margin-bottom: 1pt; }
hr { border: none; border-top: 0.5pt solid #bbb; margin: 10pt 0; }
table { border-collapse: collapse; margin: 6pt 0; }
th, td { border: 0.5pt solid #bbb; padding: 3pt 6pt; font-size: 10pt; }
th { background: #f5f5f5; }
em { font-size: 0.9em; color: #555; }
.katex-display { margin: 8pt 0; }
"""


def _build_katex_html(body_html: str) -> str:
    """Wrap an HTML body fragment in a full document with KaTeX auto-render."""
    v = _KATEX_VERSION
    return (
        '<!DOCTYPE html>\n'
        '<html><head><meta charset="utf-8">\n'
        f'<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@{v}/dist/katex.min.css">\n'
        f'<script src="https://cdn.jsdelivr.net/npm/katex@{v}/dist/katex.min.js"></script>\n'
        f'<script src="https://cdn.jsdelivr.net/npm/katex@{v}/dist/contrib/auto-render.min.js"></script>\n'
        f'<style>{_PAGE_CSS}</style>\n'
        '</head><body>\n'
        f'{body_html}\n'
        '<script>'
        'renderMathInElement(document.body, {'
        '  delimiters: ['
        '    {left: "$$", right: "$$", display: true},'
        '    {left: "$", right: "$", display: false}'
        '  ],'
        '  throwOnError: false'
        '});'
        '</script>\n'
        '</body></html>'
    )


# ---------------------------------------------------------------------------
# MCP tool
# ---------------------------------------------------------------------------


@mcp.tool()
def convert_md_to_pdf(md_file_path: str) -> str:
    """Convert a Markdown file to a styled PDF.

    Reads the .md file, converts Markdown to HTML with KaTeX math rendering,
    and produces a paginated A4 PDF via headless Chromium.  The output PDF
    is placed in the same directory with the same base name (.md -> .pdf).

    Args:
        md_file_path: Path to the Markdown (.md) file to convert.
    """
    import markdown

    p = Path(md_file_path).resolve()
    if not p.exists():
        return f"ERROR: File not found: {p}"
    if p.suffix.lower() != ".md":
        return f"ERROR: Not a Markdown file: {p}"

    md_text = p.read_text(encoding="utf-8")

    md_text, math_exprs = _extract_math(md_text)
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html_body = _restore_math_delimiters(html_body, math_exprs)
    full_html = _build_katex_html(html_body)

    pdf_path = p.with_suffix(".pdf")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.set_content(full_html, wait_until="networkidle")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                margin={
                    "top": "0.6in",
                    "bottom": "0.7in",
                    "left": "0.5in",
                    "right": "0.5in",
                },
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=(
                    '<div style="font-family: Georgia, serif; font-size: 9pt;'
                    ' text-align: center; width: 100%;">'
                    '<span class="pageNumber"></span></div>'
                ),
            )
            browser.close()
    except Exception as e:
        return f"ERROR: Failed to render PDF: {e}"

    return f"PDF saved to: {pdf_path}"
