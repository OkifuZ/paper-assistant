"""MCP tools for PDF reading: info, pages, sections, images, search, and summary saving."""

import base64
from collections import defaultdict
from pathlib import Path

from .app import mcp
from .cache import check_has_text, open_doc, resolve_path
from .toc import find_section_pages, get_toc


# ---------------------------------------------------------------------------
# pdf_info
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
        doc = open_doc(file_path)
    except (FileNotFoundError, ValueError) as e:
        return f"ERROR: {e}"

    meta = doc.metadata or {}
    has_text = check_has_text(doc)
    toc = get_toc(doc)

    lines = [
        "=== PDF Info ===",
        f"File: {resolve_path(file_path)}",
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
# pdf_read_pages
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
        doc = open_doc(file_path)
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
# pdf_read_section
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
        doc = open_doc(file_path)
    except (FileNotFoundError, ValueError) as e:
        return f"ERROR: {e}"

    toc = get_toc(doc)
    if not toc:
        return (
            "ERROR: No table of contents or section headings detected in this PDF. "
            "Use pdf_read_pages to read by page number instead."
        )

    result = find_section_pages(toc, section_title, len(doc))
    if result is None:
        available = ", ".join(f'"{e["title"]}"' for e in toc[:20])
        return (
            f'ERROR: Section "{section_title}" not found.\n'
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
        f'[Section: "{matched_title}" | '
        f"Pages {start_0 + 1}-{end_0} | {page_count} page(s) | {total_chars} chars]"
    )

    if page_count == 15:
        header += "\n(Section truncated to 15 pages. Use pdf_read_pages for remaining content.)"

    return header + "\n\n" + "\n\n".join(parts)


# ---------------------------------------------------------------------------
# pdf_get_page_images
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
        doc = open_doc(file_path)
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

    mime_map = {
        "png": "image/png",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "jxr": "image/jxr",
        "jpx": "image/jpx",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
    }

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
        mime_type = mime_map.get(ext, f"image/{ext}")

        b64 = base64.b64encode(img_bytes).decode("ascii")
        results.append({"type": "image", "data": b64, "mimeType": mime_type})
        results.append({
            "type": "text",
            "text": f"[Image {img_idx + 1}: {width}x{height}px, format={ext}]",
        })

    if not results:
        return (
            f"Page {page_number} has {len(image_list)} image(s) but all were "
            "too small (<50x50px) or unreadable."
        )

    summary = {
        "type": "text",
        "text": (
            f"[Page {page_number}: {len(results) // 2} image(s) extracted"
            f"{f', {skipped} skipped (too small/unreadable)' if skipped else ''}]"
        ),
    }
    return [summary] + results


# ---------------------------------------------------------------------------
# pdf_search
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
        doc = open_doc(file_path)
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
                matches.append(f"[Page {page_idx + 1}] {prefix}{snippet}{suffix}")

            search_start = pos + 1

    if not matches:
        return f'No results found for "{query}".'

    total_hits = sum(pages_with_hits.values())
    page_summary = ", ".join(
        f"p.{p}({c})" for p, c in sorted(pages_with_hits.items())
    )

    header = (
        f'[Search: "{query}" | {total_hits} hit(s) across '
        f"{len(pages_with_hits)} page(s): {page_summary}]"
    )

    if total_hits > max_results:
        header += f"\n(Showing first {max_results} of {total_hits} matches.)"

    return header + "\n\n" + "\n\n".join(matches)


# ---------------------------------------------------------------------------
# save_summary
# ---------------------------------------------------------------------------


@mcp.tool()
def save_summary(pdf_file_path: str, markdown_content: str) -> str:
    """Save a paper summary to the Summaries/ directory.

    Derives the output filename from the PDF's filename (not the paper title):
    strips the .pdf extension, appends '_summary.md'.
    Creates the Summaries/ directory if it does not exist.

    Args:
        pdf_file_path: The path to the source PDF (used only to derive the output name).
        markdown_content: The full Markdown summary to write.
    """
    pdf_name = Path(pdf_file_path).stem
    if not pdf_name:
        return "ERROR: Could not derive a filename from the given pdf_file_path."

    out_dir = Path.cwd() / "Summaries"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"{pdf_name}_summary.md"
    out_file.write_text(markdown_content, encoding="utf-8")

    return f"Summary saved to: {out_file}"
