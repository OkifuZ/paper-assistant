"""FastMCP application instance.

Defined separately so tool / prompt modules can import ``mcp`` without
circular-import issues with the server entry-point.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "pdf-reader",
    instructions=(
        "PDF Reader for academic papers. "
        "Always call pdf_info first to get the document structure, "
        "then use pdf_read_section or pdf_read_pages to read specific parts progressively. "
        "Do NOT read the entire document at once."
    ),
)
