# Paper Assistant

A two-part toolkit for reading and summarizing academic papers (**Simulation and Deep Learning in Computer Graphics**) inside Cursor:

1. **MCP Server** — gives AI agents structured, progressive access to PDF documents via the Model Context Protocol.
2. **Cursor Skill** — teaches the agent *how* to use those tools to produce concise, mechanism-focused paper summaries.

Each part works independently, but they are designed to be used together.

---

## MCP Tools

| Tool | Description |
|---|---|
| `pdf_info` | Metadata + table of contents (always call first) |
| `pdf_read_pages` | Read text by page range (max 10 pages per call) |
| `pdf_read_section` | Read text by section title (fuzzy matched against TOC) |
| `pdf_get_page_images` | Extract images from a page as base64 |
| `pdf_search` | Full-text search with context snippets |

## Cursor Skill: Paper Summarization

Located in `.cursor/skills/summarize-paper/`, the skill activates when you ask the agent to summarize, distill, or review a paper. It:

- Reads the paper progressively (Abstract, Introduction, then key method sections)
- Classifies the paper as Learning-oriented, Physics-oriented, or Hybrid
- Outputs a concise Markdown summary following a fixed template (see `template.md`)
- Saves output to `Summaries/`

To use the skill in another project, copy `.cursor/skills/summarize-paper/` into your project's `.cursor/skills/` directory (or run the install script below).

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

## Installation

### Option A: Zero-clone via `uvx` (recommended)

No need to clone this repo. Just configure your MCP client (see [Cursor Configuration](#cursor-configuration) below). `uvx` will automatically fetch, build, and cache the server.

### Option B: Clone and run locally

```bash
git clone https://github.com/YOUR_USERNAME/pdf-reader-mcp.git
cd pdf-reader-mcp
uv sync
```

### Option C: Install with pip

```bash
pip install git+https://github.com/YOUR_USERNAME/pdf-reader-mcp.git
```

## Cursor Configuration

Add the following to your project's `.cursor/mcp.json` file. Create the file if it doesn't exist.

### For Option A (uvx, zero-clone):

```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/YOUR_USERNAME/pdf-reader-mcp",
        "pdf-reader-mcp"
      ]
    }
  }
}
```

### For Option B (local clone):

```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/pdf-reader-mcp",
        "run",
        "pdf-reader-mcp"
      ]
    }
  }
}
```

Replace `/absolute/path/to/pdf-reader-mcp` with the actual path to your cloned repo.

### For Option C (pip installed):

```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "pdf-reader-mcp"
    }
  }
}
```

After editing `mcp.json`, restart Cursor for the MCP to take effect.

## Install Script (one-command setup)

If you cloned this repo, you can use the included install scripts to automatically configure MCP and copy the bundled Cursor skill into a target project:

**Windows (PowerShell):**

```powershell
.\install.ps1 -TargetDir "C:\path\to\your\project"
```

**macOS / Linux:**

```bash
./install.sh /path/to/your/project
```

The scripts will:

1. Verify that `uv` is installed
2. Add the `pdf-reader` MCP entry to `<target>/.cursor/mcp.json` (merges with existing config)
3. Copy the paper-summarization skill to `<target>/.cursor/skills/`
4. Create a `Summaries/` directory in the target project

If no target directory is given, the scripts default to the current directory.

## License

MIT
