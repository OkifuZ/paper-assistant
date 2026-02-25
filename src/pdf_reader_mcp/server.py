"""
PDF Reader MCP Server - Structured, progressive PDF reading for academic papers.

Provides 5 tools for agent-driven incremental access to PDF content:
  pdf_info          - metadata + TOC (always call first)
  pdf_read_pages    - read text by page range
  pdf_read_section  - read text by section title
  pdf_get_page_images - extract images from a page
  pdf_search        - search text with context snippets
"""

import base64
import re
from collections import defaultdict
from pathlib import Path
from statistics import median

import fitz  # PyMuPDF
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

# ---------------------------------------------------------------------------
# PDF Document Cache
# ---------------------------------------------------------------------------

_doc_cache: dict[str, fitz.Document] = {}


def _resolve_path(file_path: str) -> str:
    """Resolve and validate a PDF file path."""
    p = Path(file_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {p}")
    return str(p)


def _open_doc(file_path: str) -> fitz.Document:
    """Open a PDF, returning a cached document if available."""
    key = _resolve_path(file_path)
    if key in _doc_cache:
        return _doc_cache[key]
    doc = fitz.open(key)
    _doc_cache[key] = doc
    return doc


def _check_has_text(doc: fitz.Document, sample_pages: int = 5) -> bool:
    """Check if the PDF contains extractable text."""
    total_chars = 0
    for i in range(min(sample_pages, len(doc))):
        total_chars += len(doc[i].get_text().strip())
    return total_chars >= 50


# ---------------------------------------------------------------------------
# Heading Detection (fallback when PDF has no TOC)
# ---------------------------------------------------------------------------


def _detect_headings(doc: fitz.Document) -> list[dict]:
    """
    Heuristically detect section headings by analyzing font sizes.
    Returns a list of {"title": str, "page": int (1-based), "level": int}.
    """
    font_sizes: list[float] = []
    spans_info: list[dict] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_text = ""
                max_size = 0.0
                is_bold = False
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                    size = span.get("size", 0)
                    if size > max_size:
                        max_size = size
                    flags = span.get("flags", 0)
                    if flags & (1 << 4):  # bold bit
                        is_bold = True
                    font_sizes.append(size)

                line_text = line_text.strip()
                if line_text:
                    spans_info.append({
                        "text": line_text,
                        "size": max_size,
                        "bold": is_bold,
                        "page": page_idx,
                    })

    if not font_sizes:
        return []

    median_size = median(font_sizes)
    heading_threshold = median_size * 1.25

    numbered_heading_re = re.compile(
        r"^(\d+\.?\d*\.?\d*)\s+[A-Z]"
    )
    uppercase_heading_re = re.compile(
        r"^[A-Z][A-Z\s:&-]{4,}$"
    )

    headings: list[dict] = []
    for info in spans_info:
        text = info["text"]
        size = info["size"]

        if len(text) > 120 or len(text) < 2:
            continue

        is_heading = False
        level = 2

        if size >= heading_threshold:
            is_heading = True
            level = 1 if size >= median_size * 1.5 else 2

        if not is_heading and info["bold"] and size >= median_size:
            if numbered_heading_re.match(text) or uppercase_heading_re.match(text):
                is_heading = True
                level = 1

        if not is_heading and numbered_heading_re.match(text) and size >= median_size:
            is_heading = True
            level = 1

        if is_heading:
            headings.append({
                "title": text,
                "page": info["page"] + 1,
                "level": level,
            })

    return headings


def _get_toc(doc: fitz.Document) -> list[dict]:
    """
    Get the table of contents. Uses the built-in outline first,
    falls back to heuristic heading detection.
    Returns list of {"level": int, "title": str, "page": int (1-based)}.
    """
    raw_toc = doc.get_toc(simple=True)
    if raw_toc:
        return [
            {"level": entry[0], "title": entry[1].strip(), "page": entry[2]}
            for entry in raw_toc
            if entry[1].strip()
        ]
    return _detect_headings(doc)


def _find_section_pages(
    toc: list[dict], section_title: str, total_pages: int
) -> tuple[int, int] | None:
    """
    Find the page range for a section. Fuzzy-matches section_title against TOC entries.
    Returns (start_page_0based, end_page_0based_exclusive) or None.
    """
    query = section_title.lower().strip()
    query_nospace = re.sub(r"\s+", "", query)

    best_idx = -1
    best_score = 0.0

    for i, entry in enumerate(toc):
        title_lower = entry["title"].lower().strip()
        title_nospace = re.sub(r"\s+", "", title_lower)

        if query == title_lower or query_nospace == title_nospace:
            best_idx = i
            break

        if query in title_lower or title_lower in query:
            score = len(query) / max(len(title_lower), 1)
            if score > best_score:
                best_score = score
                best_idx = i
            continue

        query_words = set(query.split())
        title_words = set(title_lower.split())
        overlap = query_words & title_words
        if overlap:
            score = len(overlap) / max(len(query_words | title_words), 1)
            if score > best_score:
                best_score = score
                best_idx = i

    if best_idx < 0:
        return None

    start_page = toc[best_idx]["page"] - 1
    matched_level = toc[best_idx]["level"]

    end_page = total_pages
    for j in range(best_idx + 1, len(toc)):
        if toc[j]["level"] <= matched_level:
            end_page = toc[j]["page"] - 1
            break

    return (start_page, end_page)


# ---------------------------------------------------------------------------
# Tool 1: pdf_info
# ---------------------------------------------------------------------------


@mcp.tool()
def pdf_info(file_path: str) -> str:
    """Open a PDF and return its metadata and table of contents.

    ALWAYS call this tool first before reading any content.
    Returns: page count, title, author, whether it has extractable text,
    and the table of contents with section titles and page numbers.

    Args:
        file_path: Absolute or relative path to the PDF file.
    """
    try:
        doc = _open_doc(file_path)
    except (FileNotFoundError, ValueError) as e:
        return f"ERROR: {e}"

    meta = doc.metadata or {}
    has_text = _check_has_text(doc)
    toc = _get_toc(doc)

    lines = [
        f"=== PDF Info ===",
        f"File: {_resolve_path(file_path)}",
        f"Pages: {len(doc)}",
        f"Title: {meta.get('title', '') or '(unknown)'}",
        f"Author: {meta.get('author', '') or '(unknown)'}",
        f"Subject: {meta.get('subject', '') or '(unknown)'}",
        f"Creation Date: {meta.get('creationDate', '') or '(unknown)'}",
        f"Has Extractable Text: {has_text}",
    ]

    if not has_text:
        lines.append("")
        lines.append(
            "WARNING: This PDF appears to be scanned or image-only. "
            "Text extraction will return little or no content. "
            "Consider using OCR tools for this document."
        )

    lines.append("")
    if toc:
        lines.append(f"=== Table of Contents ({len(toc)} entries) ===")
        for entry in toc:
            indent = "  " * (entry["level"] - 1)
            lines.append(f"{indent}{entry['title']}  [page {entry['page']}]")
    else:
        lines.append("=== Table of Contents ===")
        lines.append("(No TOC detected. Use pdf_read_pages to read by page number.)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: pdf_read_pages
# ---------------------------------------------------------------------------


@mcp.tool()
def pdf_read_pages(file_path: str, start_page: int, end_page: int = 0) -> str:
    """Read text from a range of pages in the PDF.

    Pages are 1-based. Maximum 10 pages per call to avoid context overload.
    If end_page is 0 or not provided, only start_page is read.

    Args:
        file_path: Path to the PDF file.
        start_page: First page to read (1-based).
        end_page: Last page to read (1-based, inclusive). 0 means same as start_page.
    """
    try:
        doc = _open_doc(file_path)
    except (FileNotFoundError, ValueError) as e:
        return f"ERROR: {e}"

    total = len(doc)
    if end_page <= 0:
        end_page = start_page

    if start_page < 1 or start_page > total:
        return f"ERROR: start_page {start_page} out of range (1-{total})."
    if end_page < start_page:
        return f"ERROR: end_page ({end_page}) < start_page ({start_page})."
    if end_page > total:
        end_page = total

    page_count = end_page - start_page + 1
    if page_count > 10:
        end_page = start_page + 9
        page_count = 10

    parts: list[str] = []
    total_chars = 0
    for i in range(start_page - 1, end_page):
        page = doc[i]
        text = page.get_text().strip()
        total_chars += len(text)
        parts.append(f"--- Page {i + 1} ---")
        parts.append(text if text else "(no text on this page)")

    header = (
        f"[Pages {start_page}-{end_page} of {total} | "
        f"{page_count} page(s) | {total_chars} chars]"
    )
    return header + "\n\n" + "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Tool 3: pdf_read_section
# ---------------------------------------------------------------------------


@mcp.tool()
def pdf_read_section(file_path: str, section_title: str) -> str:
    """Read a specific section of the PDF by its title from the table of contents.

    Fuzzy-matches the section_title against TOC entries. Use pdf_info first
    to see available sections. Falls back to heuristic heading detection
    if the PDF has no formal outline.

    Args:
        file_path: Path to the PDF file.
        section_title: Title of the section to read (fuzzy matched).
    """
    try:
        doc = _open_doc(file_path)
    except (FileNotFoundError, ValueError) as e:
        return f"ERROR: {e}"

    toc = _get_toc(doc)
    if not toc:
        return (
            "ERROR: No table of contents or section headings detected in this PDF. "
            "Use pdf_read_pages to read by page number instead."
        )

    result = _find_section_pages(toc, section_title, len(doc))
    if result is None:
        available = ", ".join(f'"{e["title"]}"' for e in toc[:20])
        return (
            f"ERROR: Section \"{section_title}\" not found.\n"
            f"Available sections: {available}"
        )

    start_0, end_0 = result
    matched_entry = None
    for entry in toc:
        if entry["page"] - 1 == start_0:
            matched_entry = entry
            break

    page_count = end_0 - start_0
    if page_count > 15:
        end_0 = start_0 + 15
        page_count = 15

    parts: list[str] = []
    total_chars = 0
    for i in range(start_0, end_0):
        text = doc[i].get_text().strip()
        total_chars += len(text)
        parts.append(f"--- Page {i + 1} ---")
        parts.append(text if text else "(no text on this page)")

    matched_title = matched_entry["title"] if matched_entry else section_title
    header = (
        f"[Section: \"{matched_title}\" | "
        f"Pages {start_0 + 1}-{end_0} | {page_count} page(s) | {total_chars} chars]"
    )

    if page_count == 15:
        header += "\n(Section truncated to 15 pages. Use pdf_read_pages for remaining content.)"

    return header + "\n\n" + "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Tool 4: pdf_get_page_images
# ---------------------------------------------------------------------------


@mcp.tool()
def pdf_get_page_images(file_path: str, page_number: int) -> list | str:
    """Extract images from a specific page of the PDF.

    Returns images as base64-encoded data. Filters out tiny decorative images
    (smaller than 50x50 pixels). Pages are 1-based.

    Args:
        file_path: Path to the PDF file.
        page_number: The page number to extract images from (1-based).
    """
    try:
        doc = _open_doc(file_path)
    except (FileNotFoundError, ValueError) as e:
        return f"ERROR: {e}"

    total = len(doc)
    if page_number < 1 or page_number > total:
        return f"ERROR: page_number {page_number} out of range (1-{total})."

    page = doc[page_number - 1]
    image_list = page.get_images(full=True)

    if not image_list:
        return f"No images found on page {page_number}."

    results = []
    skipped = 0

    for img_idx, img_info in enumerate(image_list):
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
        except Exception:
            skipped += 1
            continue

        if not base_image or not base_image.get("image"):
            skipped += 1
            continue

        width = base_image.get("width", 0)
        height = base_image.get("height", 0)

        if width < 50 or height < 50:
            skipped += 1
            continue

        img_bytes = base_image["image"]
        ext = base_image.get("ext", "png")
        mime_map = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "jxr": "image/jxr",
            "jpx": "image/jpx",
            "bmp": "image/bmp",
            "tiff": "image/tiff",
        }
        mime_type = mime_map.get(ext, f"image/{ext}")

        b64 = base64.b64encode(img_bytes).decode("ascii")
        results.append({
            "type": "image",
            "data": b64,
            "mimeType": mime_type,
        })
        results.append({
            "type": "text",
            "text": (
                f"[Image {img_idx + 1}: {width}x{height}px, format={ext}]"
            ),
        })

    if not results:
        return f"Page {page_number} has {len(image_list)} image(s) but all were too small (<50x50px) or unreadable."

    summary = {
        "type": "text",
        "text": (
            f"[Page {page_number}: {len(results) // 2} image(s) extracted"
            f"{f', {skipped} skipped (too small/unreadable)' if skipped else ''}]"
        ),
    }
    return [summary] + results


# ---------------------------------------------------------------------------
# Tool 5: pdf_search
# ---------------------------------------------------------------------------


@mcp.tool()
def pdf_search(file_path: str, query: str, max_results: int = 10) -> str:
    """Search for text in the PDF and return matching snippets with context.

    Returns up to max_results matches, each with the page number and
    surrounding context (~100 characters before and after the match).

    Args:
        file_path: Path to the PDF file.
        query: The text to search for (case-insensitive).
        max_results: Maximum number of results to return (default 10).
    """
    try:
        doc = _open_doc(file_path)
    except (FileNotFoundError, ValueError) as e:
        return f"ERROR: {e}"

    if not query.strip():
        return "ERROR: Search query cannot be empty."

    query_lower = query.lower()
    matches: list[str] = []
    pages_with_hits: dict[int, int] = defaultdict(int)

    for page_idx in range(len(doc)):
        text = doc[page_idx].get_text()
        text_lower = text.lower()
        search_start = 0

        while True:
            pos = text_lower.find(query_lower, search_start)
            if pos < 0:
                break

            pages_with_hits[page_idx + 1] += 1

            if len(matches) < max_results:
                ctx_start = max(0, pos - 100)
                ctx_end = min(len(text), pos + len(query) + 100)
                snippet = text[ctx_start:ctx_end].replace("\n", " ").strip()

                prefix = "..." if ctx_start > 0 else ""
                suffix = "..." if ctx_end < len(text) else ""
                matches.append(
                    f"[Page {page_idx + 1}] {prefix}{snippet}{suffix}"
                )

            search_start = pos + 1

    if not matches:
        return f"No results found for \"{query}\"."

    total_hits = sum(pages_with_hits.values())
    page_summary = ", ".join(
        f"p.{p}({c})" for p, c in sorted(pages_with_hits.items())
    )

    header = (
        f"[Search: \"{query}\" | {total_hits} hit(s) across "
        f"{len(pages_with_hits)} page(s): {page_summary}]"
    )

    if total_hits > max_results:
        header += f"\n(Showing first {max_results} of {total_hits} matches.)"

    return header + "\n\n" + "\n\n".join(matches)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
