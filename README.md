# Paper Assistant

A toolkit for reading and summarizing academic papers (**Simulation & Deep Learning in Computer Graphics**) inside Cursor, combining an MCP server with a Cursor agent skill.

## Quick Start

Requires **Python 3.12+**. Clone the repo, then run:

```powershell
# Windows
.\install.ps1

# macOS / Linux
./install.sh
```

This handles everything — finding/installing `uv`, syncing dependencies, configuring the MCP server, and creating working directories. Restart Cursor after it finishes.

**Usage:**
1. Ask the agent: *"Summarize C:\Notes\papers\my_paper.pdf"* (PDFs can live anywhere)
2. The summary appears in `Summaries/my_paper_summary.md`

## MCP Tools (agent-facing)

These tools are exposed to the AI agent via MCP — they are not CLI commands for humans. The agent calls them automatically when you ask it to read or summarize a paper.

| Tool | Description |
|---|---|
| `pdf_info` | Metadata + table of contents (always call first) |
| `pdf_read_pages` | Read text by page range (max 10 pages per call) |
| `pdf_read_section` | Read text by section title (fuzzy matched against TOC) |
| `pdf_get_page_images` | Extract images from a page as base64 |
| `pdf_search` | Full-text search with context snippets |
| `save_summary` | Save a Markdown summary to `Summaries/<pdf_name>_summary.md` (auto-creates folder) |

| Prompt | Description |
|---|---|
| `read_paper` | Progressive reading protocol — metadata/TOC first, then drills into sections. Accepts `file_path` and optional `question`. |

## Cursor Skill

Located in `.cursor/skills/summarize-paper/`. Activates when you ask the agent to summarize, distill, or review a paper. It reads progressively, classifies the paper (Learning / Physics / Hybrid), and outputs a structured Markdown summary following `template.md`.

## Project Layout

```
PaperAssistant/
├── Summaries/           ← Generated summaries land here (gitignored)
├── src/pdf_reader_mcp/  ← MCP server source
├── .cursor/
│   ├── mcp.json         ← MCP client config (gitignored, machine-local)
│   └── skills/          ← Cursor agent skills
├── pyproject.toml
└── uv.lock
```

## Manual Installation

If you prefer not to use the install script:

```bash
pip install uv              # or see https://docs.astral.sh/uv
uv sync                     # install dependencies into .venv/
uv run pdf-reader-mcp       # verify server starts (Ctrl+C to stop)
```

Then create `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "/absolute/path/to/uv.exe",
      "args": ["--directory", "/absolute/path/to/PaperAssistant", "run", "pdf-reader-mcp"]
    }
  }
}
```

Use absolute paths to avoid PATH issues when Cursor spawns the process. Restart Cursor after editing.

> **Windows PATH note:** If `uv` is not recognized after `pip install uv`, find the binary with:
> `python -c "from uv import find_uv_bin; print(find_uv_bin())"`

> **Transient install error:** On some Windows setups the first `uv sync` fails with an OS permissions error (antivirus). Simply retry.

## Gitignored Paths

| Path | Reason |
|---|---|
| `.venv/` | Local virtual environment |
| `.cursor/mcp.json` | Machine-local absolute paths |
| `Summaries/*` | Generated output |
| `__pycache__/`, `build/`, `dist/` | Python build artifacts |

<details>
<summary><strong>What <code>install.ps1</code> does step by step</strong></summary>

1. **Find `uv`** — checks PATH via `Get-Command uv`. If not found, locates it through `python -c "from uv import find_uv_bin; ..."`. If still missing, auto-installs via `pip install uv`.
2. **Resolve directories** — resolves `TargetDir` (defaults to `.`) and `ScriptDir` (where `install.ps1` lives) to absolute paths.
3. **`uv sync`** — runs `uv sync` in the repo directory to create `.venv/` and install all dependencies (`mcp[cli]`, `pymupdf`, etc.). Automatically retries once on failure (works around a transient Windows permissions/antivirus error).
4. **Verify MCP server** — starts `uv run pdf-reader-mcp`, waits 3 seconds to confirm it doesn't crash, then kills the process.
5. **Write `.cursor/mcp.json`** — creates or merges the `pdf-reader` MCP entry using the **absolute path** to `uv.exe` as the command (avoids PATH resolution issues when Cursor spawns the process).
6. **Copy skill files** — copies `.cursor/skills/summarize-paper/` from the repo to the target project. Skipped when target == repo (files already in place).
7. **Create `Summaries/`** — creates the output directory with a `.gitkeep` file so git tracks the empty folder while ignoring its contents.

</details>

## License

MIT
