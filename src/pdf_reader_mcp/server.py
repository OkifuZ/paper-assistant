"""PDF Reader MCP Server - Structured, progressive PDF reading for academic papers.

Provides tools for agent-driven incremental access to PDF content:
  pdf_info          - metadata + TOC (always call first)
  pdf_read_pages    - read text by page range
  pdf_read_section  - read text by section title
  pdf_get_page_images - extract images from a page
  pdf_search        - search text with context snippets
  save_summary      - persist a Markdown summary
  convert_md_to_pdf - render Markdown to styled PDF
"""

from .app import mcp  # noqa: F401 – re-exported for external use

# Importing these modules registers their @mcp.tool / @mcp.prompt decorators.
import pdf_reader_mcp.tools  # noqa: F401
import pdf_reader_mcp.convert  # noqa: F401
import pdf_reader_mcp.prompts  # noqa: F401


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
