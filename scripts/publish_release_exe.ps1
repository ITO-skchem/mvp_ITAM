# Creates a GitHub Release and uploads exec\ITAM_Portal.exe as the only asset.
# Prerequisites (one of):
#   - Run once:  gh auth login
#   - Or set env: $env:GH_TOKEN = "<classic PAT with repo scope>"
#
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\publish_release_exe.ps1
# Optional: -Tag "portable-2026-05-15"  (default: portable-UTC timestamp)

param(
    [string]$Tag = "",
    [string]$ExeRelative = "exec\ITAM_Portal.exe"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$GhCandidates = @(
    (Join-Path $env:ProgramFiles "GitHub CLI\gh.exe"),
    "gh"
)
$Gh = $GhCandidates | Where-Object { $_ -eq "gh" -or (Test-Path $_) } | Select-Object -First 1
if (-not $Gh) {
    Write-Error "GitHub CLI (gh) not found. Install from https://cli.github.com/ or winget install GitHub.cli"
}

function Get-GitHubRepoSlug {
    $url = (& git -C $RepoRoot remote get-url origin).Trim()
    if ($url -match "github\.com[:/]([^/]+)/([^/.]+)") {
        return "$($matches[1])/$($matches[2])"
    }
    throw "Could not parse owner/repo from git remote origin: $url"
}

$exe = Join-Path $RepoRoot $ExeRelative
if (-not (Test-Path $exe)) {
    Write-Error "Missing executable: $exe`nRun: powershell -ExecutionPolicy Bypass -File .\scripts\build_exec.ps1"
}

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
& $Gh auth status *> $null
$authExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($authExit -ne 0 -and -not $env:GH_TOKEN -and -not $env:GITHUB_TOKEN) {
    Write-Error @"
Not authenticated for GitHub API.
  Run:  gh auth login
  Or:  `$env:GH_TOKEN = '<PAT with repo scope>'
"@
}

if (-not $Tag) {
    $Tag = "portable-" + [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss")
}

$repo = Get-GitHubRepoSlug
$title = "Portable Windows build (ITAM_Portal.exe)"
$notes = @"
**ITAM_Portal.exe** — PyInstaller onefile (Python not required on the target PC).

- Place **db.sqlite3** in the same folder as the exe (see ``scripts\build_exec.ps1`` in the repo).
- Default URL after start: http://127.0.0.1:8000/

Repository: https://github.com/$repo
"@

Write-Host "Creating release $Tag on $repo ..."
& $Gh release create $Tag $exe --repo $repo --title $title --notes $notes
Write-Host "Done. Open: https://github.com/$repo/releases/tag/$Tag"
