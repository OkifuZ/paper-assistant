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

# ── 1. Find uv (handle Windows PATH issues) ─────────────────────────────────

$uvBin = $null

$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    $uvBin = $uvCmd.Source
} else {
    Write-Host "'uv' not on PATH — trying to locate via Python..." -ForegroundColor Yellow
    try {
        $uvBin = & python -c "from uv import find_uv_bin; print(find_uv_bin())" 2>$null
        if ($uvBin) { $uvBin = $uvBin.Trim() }
    } catch {}
}

if (-not $uvBin -or -not (Test-Path $uvBin)) {
    Write-Host "'uv' not found. Attempting install via pip..." -ForegroundColor Yellow
    & python -m pip install uv --quiet
    try {
        $uvBin = & python -c "from uv import find_uv_bin; print(find_uv_bin())" 2>$null
        if ($uvBin) { $uvBin = $uvBin.Trim() }
    } catch {}
    if (-not $uvBin -or -not (Test-Path $uvBin)) {
        Write-Host "ERROR: Could not install or locate 'uv'." -ForegroundColor Red
        Write-Host "Install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

Write-Host "[ok] uv found: $uvBin  ($(& $uvBin --version))" -ForegroundColor Green

# ── 2. Resolve target directory ──────────────────────────────────────────────

$TargetDir = (Resolve-Path $TargetDir).Path
Write-Host "Target project : $TargetDir"
Write-Host "Repo directory : $ScriptDir"

$cursorDir = Join-Path $TargetDir ".cursor"
if (-not (Test-Path $cursorDir)) {
    New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
}

# ── 3. Sync dependencies ────────────────────────────────────────────────────

Write-Host ""
Write-Host "Running 'uv sync' in $ScriptDir ..." -ForegroundColor Cyan
& $uvBin --directory $ScriptDir sync
if ($LASTEXITCODE -ne 0) {
    Write-Host "First attempt failed (may be transient on Windows). Retrying..." -ForegroundColor Yellow
    & $uvBin --directory $ScriptDir sync
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: 'uv sync' failed." -ForegroundColor Red
        exit 1
    }
}
Write-Host "[ok] Dependencies synced" -ForegroundColor Green

# ── 4. Verify MCP server can start ──────────────────────────────────────────

Write-Host ""
Write-Host "Verifying MCP server starts..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $uvBin -ArgumentList "--directory", $ScriptDir, "run", "pdf-reader-mcp" `
    -NoNewWindow -PassThru -RedirectStandardError (Join-Path $env:TEMP "mcp_stderr.txt")
Start-Sleep -Seconds 3

if ($proc.HasExited -and $proc.ExitCode -ne 0) {
    $stderr = Get-Content (Join-Path $env:TEMP "mcp_stderr.txt") -Raw -ErrorAction SilentlyContinue
    Write-Host "ERROR: MCP server exited with code $($proc.ExitCode)" -ForegroundColor Red
    if ($stderr) { Write-Host $stderr -ForegroundColor Red }
    exit 1
}

if (-not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}
Write-Host "[ok] MCP server starts successfully" -ForegroundColor Green

# ── 5. Write / merge .cursor/mcp.json (absolute paths) ──────────────────────

$mcpJsonPath = Join-Path $cursorDir "mcp.json"

$uvBinEscaped = $uvBin.Replace('\', '\\')
$scriptDirEscaped = $ScriptDir.Replace('\', '\\')

function Write-McpJson {
    param([string]$Path, [hashtable]$Servers)
    $entries = @()
    foreach ($name in ($Servers.Keys | Sort-Object)) {
        $srv = $Servers[$name]
        $argsJson = ($srv.args | ForEach-Object { "        `"$_`"" }) -join ",`n"
        $entries += @"
    "$name": {
      "command": "$($srv.command)",
      "args": [
$argsJson
      ]
    }
"@
    }
    $json = "{{`n  `"mcpServers`": {{`n{0}`n  }}`n}}`n" -f ($entries -join ",`n")
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
}

$newServer = @{
    command = $uvBinEscaped
    args    = @("--directory", $scriptDirEscaped, "run", "pdf-reader-mcp")
}

$servers = @{}
if (Test-Path $mcpJsonPath) {
    $existing = Get-Content $mcpJsonPath -Raw | ConvertFrom-Json
    if ($existing.mcpServers) {
        foreach ($prop in $existing.mcpServers.PSObject.Properties) {
            $servers[$prop.Name] = @{
                command = $prop.Value.command
                args    = @($prop.Value.args)
            }
        }
    }
    $servers["pdf-reader"] = $newServer
    Write-McpJson -Path $mcpJsonPath -Servers $servers
    Write-Host "[ok] Merged pdf-reader entry into existing $mcpJsonPath" -ForegroundColor Green
} else {
    $servers["pdf-reader"] = $newServer
    Write-McpJson -Path $mcpJsonPath -Servers $servers
    Write-Host "[ok] Created $mcpJsonPath" -ForegroundColor Green
}

# ── 6. Copy skill files (skip if target == repo) ────────────────────────────

$srcSkill = Join-Path (Join-Path (Join-Path $ScriptDir ".cursor") "skills") "summarize-paper"
$dstSkill = Join-Path (Join-Path $cursorDir "skills") "summarize-paper"

$srcNorm = (Resolve-Path $srcSkill -ErrorAction SilentlyContinue).Path
$dstNorm = $dstSkill
try { $dstNorm = (Resolve-Path $dstSkill -ErrorAction SilentlyContinue).Path } catch {}

if ($srcNorm -eq $dstNorm) {
    Write-Host "[ok] Skill already in place (target == repo)" -ForegroundColor Green
} elseif (Test-Path $srcSkill) {
    $skillsParent = Join-Path $cursorDir "skills"
    if (-not (Test-Path $skillsParent)) {
        New-Item -ItemType Directory -Path $skillsParent -Force | Out-Null
    }
    Copy-Item -Path $srcSkill -Destination $dstSkill -Recurse -Force
    Write-Host "[ok] Copied summarize-paper skill to $dstSkill" -ForegroundColor Green
} else {
    Write-Host "[skip] Skill folder not found at $srcSkill" -ForegroundColor Yellow
}

# ── 7. Create Summaries directory ────────────────────────────────────────────

$summariesDir = Join-Path $TargetDir "Summaries"
if (-not (Test-Path $summariesDir)) {
    New-Item -ItemType Directory -Path $summariesDir -Force | Out-Null
}
$gitkeep = Join-Path $summariesDir ".gitkeep"
if (-not (Test-Path $gitkeep)) {
    New-Item -ItemType File -Path $gitkeep -Force | Out-Null
}
Write-Host "[ok] Summaries/ ready" -ForegroundColor Green

# ── Done ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Setup complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  uv        : $uvBin"
Write-Host "  mcp.json  : $mcpJsonPath"
Write-Host "  Summaries : $(Join-Path $TargetDir 'Summaries')"
Write-Host ""
Write-Host "Restart Cursor for the MCP to take effect." -ForegroundColor Cyan
