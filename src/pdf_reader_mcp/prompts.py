"""MCP prompts for guided paper reading."""

from .app import mcp


@mcp.prompt()
def read_paper(file_path: str, question: str = "") -> str:
    """Guided progressive reading of an academic paper.

    Instructs the model to read the paper incrementally using the PDF tools,
    starting with metadata/TOC and drilling into specific sections as needed.

    Args:
        file_path: Absolute or relative path to the PDF file.
        question: Optional specific question to focus the reading on.
    """
    prompt = (
        f"Read the academic paper at: {file_path}\n\n"
        "Follow this progressive reading protocol:\n"
        "1. Call pdf_info to get metadata and table of contents\n"
        "2. Read the Abstract to understand the paper's scope\n"
        "3. Based on the TOC and the user's question, select the most relevant sections\n"
        "4. Read those sections one at a time via pdf_read_section\n"
        "5. Use pdf_search to locate specific terms or concepts if needed\n"
        "6. Do NOT read the entire paper at once — only read what is needed\n"
    )
    if question:
        prompt += f"\nThe user wants to know: {question}"
    else:
        prompt += (
            "\nNo specific question was provided. "
            "Give an overview: start with Abstract, then read Introduction, "
            "and summarize the key contributions before asking the user what to dive into."
        )
    return prompt
