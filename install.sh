#!/usr/bin/env bash
#
# Set up pdf-reader-mcp and the paper-summarization skill in a target
# Cursor project.
#
# Usage:
#   ./install.sh [target_project_dir]
#
# If target_project_dir is omitted, defaults to the current directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

# ── 1. Check uv ──────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "ERROR: 'uv' is not installed or not on PATH."
    echo "Install it from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi
echo "[ok] uv found: $(uv --version)"

# ── 2. Resolve paths ─────────────────────────────────────────────────────────
echo "Target project: $TARGET_DIR"

CURSOR_DIR="$TARGET_DIR/.cursor"
mkdir -p "$CURSOR_DIR"

# ── 3. Write / merge .cursor/mcp.json ────────────────────────────────────────
MCP_JSON="$CURSOR_DIR/mcp.json"

NEW_ENTRY=$(cat <<EOJSON
{
  "command": "uv",
  "args": ["--directory", "$SCRIPT_DIR", "run", "pdf-reader-mcp"]
}
EOJSON
)

if [ -f "$MCP_JSON" ]; then
    if command -v jq &>/dev/null; then
        jq --argjson entry "$NEW_ENTRY" \
           '.mcpServers["pdf-reader"] = $entry' \
           "$MCP_JSON" > "${MCP_JSON}.tmp" && mv "${MCP_JSON}.tmp" "$MCP_JSON"
        echo "[ok] Merged pdf-reader entry into existing $MCP_JSON"
    else
        echo "[warn] jq not found -- cannot merge into existing mcp.json."
        echo "       Please add the pdf-reader entry manually. See README.md."
    fi
else
    cat > "$MCP_JSON" <<EOJSON
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uv",
      "args": ["--directory", "$SCRIPT_DIR", "run", "pdf-reader-mcp"]
    }
  }
}
EOJSON
    echo "[ok] Created $MCP_JSON"
fi

# ── 4. Copy skill files ──────────────────────────────────────────────────────
SRC_SKILL="$SCRIPT_DIR/.cursor/skills/summarize-paper"
DST_SKILL="$CURSOR_DIR/skills/summarize-paper"

if [ -d "$SRC_SKILL" ]; then
    mkdir -p "$CURSOR_DIR/skills"
    cp -r "$SRC_SKILL" "$DST_SKILL"
    echo "[ok] Copied summarize-paper skill to $DST_SKILL"
else
    echo "[skip] Skill folder not found at $SRC_SKILL"
fi

# ── 5. Create Summaries directory ─────────────────────────────────────────────
SUMMARIES_DIR="$TARGET_DIR/Summaries"
if [ ! -d "$SUMMARIES_DIR" ]; then
    mkdir -p "$SUMMARIES_DIR"
    echo "[ok] Created $SUMMARIES_DIR"
else
    echo "[ok] Summaries/ already exists"
fi

echo ""
echo "Done! Restart Cursor for the MCP to take effect."
