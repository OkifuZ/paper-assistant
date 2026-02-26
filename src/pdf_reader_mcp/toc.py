"""Table-of-contents extraction and section-page lookup."""

import re
from statistics import median

import fitz  # PyMuPDF


def detect_headings(doc: fitz.Document) -> list[dict]:
    """Heuristically detect section headings by analysing font sizes.

    Returns a list of ``{"title": str, "page": int (1-based), "level": int}``.
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

    numbered_heading_re = re.compile(r"^(\d+\.?\d*\.?\d*)\s+[A-Z]")
    uppercase_heading_re = re.compile(r"^[A-Z][A-Z\s:&-]{4,}$")

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


def get_toc(doc: fitz.Document) -> list[dict]:
    """Get the table of contents.

    Uses the built-in outline first, falls back to heuristic heading
    detection.  Returns ``[{"level": int, "title": str, "page": int}]``
    with 1-based page numbers.
    """
    raw_toc = doc.get_toc(simple=True)
    if raw_toc:
        return [
            {"level": entry[0], "title": entry[1].strip(), "page": entry[2]}
            for entry in raw_toc
            if entry[1].strip()
        ]
    return detect_headings(doc)


def find_section_pages(
    toc: list[dict], section_title: str, total_pages: int,
) -> tuple[int, int] | None:
    """Find the page range for a section (fuzzy match).

    Returns ``(start_page_0based, end_page_0based_exclusive)`` or ``None``.
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
