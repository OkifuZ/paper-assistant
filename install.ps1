<#
.SYNOPSIS
    Set up pdf-reader-mcp and the paper-summarization skill in a target Cursor project.
.PARAMETER TargetDir
    Path to the project where MCP config and skill files should be installed.
    Defaults to the current directory.
#>
param(
    [string]$TargetDir = "."
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# ── 1. Check uv ──────────────────────────────────────────────────────────────
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: 'uv' is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Install it from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}
Write-Host "[ok] uv found: $(uv --version)" -ForegroundColor Green

# ── 2. Resolve target directory ───────────────────────────────────────────────
$TargetDir = (Resolve-Path $TargetDir).Path
Write-Host "Target project: $TargetDir"

$cursorDir = Join-Path $TargetDir ".cursor"
if (-not (Test-Path $cursorDir)) {
    New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
}

# ── 3. Write / merge .cursor/mcp.json ────────────────────────────────────────
$mcpJsonPath = Join-Path $cursorDir "mcp.json"
$repoDir = $ScriptDir.Replace('\', '\\')

$newEntry = @{
    command = "uv"
    args    = @("--directory", $ScriptDir, "run", "pdf-reader-mcp")
}

if (Test-Path $mcpJsonPath) {
    $existing = Get-Content $mcpJsonPath -Raw | ConvertFrom-Json
    if (-not $existing.mcpServers) {
        $existing | Add-Member -NotePropertyName mcpServers -NotePropertyValue @{} -Force
    }
    $existing.mcpServers | Add-Member -NotePropertyName "pdf-reader" -NotePropertyValue $newEntry -Force
    $existing | ConvertTo-Json -Depth 10 | Set-Content $mcpJsonPath -Encoding UTF8
    Write-Host "[ok] Merged pdf-reader entry into existing $mcpJsonPath" -ForegroundColor Green
} else {
    $config = @{ mcpServers = @{ "pdf-reader" = $newEntry } }
    $config | ConvertTo-Json -Depth 10 | Set-Content $mcpJsonPath -Encoding UTF8
    Write-Host "[ok] Created $mcpJsonPath" -ForegroundColor Green
}

# ── 4. Copy skill files ──────────────────────────────────────────────────────
$srcSkill = Join-Path $ScriptDir ".cursor" "skills" "summarize-paper"
$dstSkill = Join-Path $cursorDir "skills" "summarize-paper"

if (Test-Path $srcSkill) {
    if (-not (Test-Path (Join-Path $cursorDir "skills"))) {
        New-Item -ItemType Directory -Path (Join-Path $cursorDir "skills") -Force | Out-Null
    }
    Copy-Item -Path $srcSkill -Destination $dstSkill -Recurse -Force
    Write-Host "[ok] Copied summarize-paper skill to $dstSkill" -ForegroundColor Green
} else {
    Write-Host "[skip] Skill folder not found at $srcSkill" -ForegroundColor Yellow
}

# ── 5. Create Summaries directory ─────────────────────────────────────────────
$summariesDir = Join-Path $TargetDir "Summaries"
if (-not (Test-Path $summariesDir)) {
    New-Item -ItemType Directory -Path $summariesDir -Force | Out-Null
    Write-Host "[ok] Created $summariesDir" -ForegroundColor Green
} else {
    Write-Host "[ok] Summaries/ already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done! Restart Cursor for the MCP to take effect." -ForegroundColor Cyan
