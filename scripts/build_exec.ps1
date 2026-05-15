$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$venvPy = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Error "venv not found at $venvPy — create venv and pip install -r requirements.txt first."
}

& $venvPy -m pip install --quiet pyinstaller
& $venvPy -m PyInstaller --noconfirm (Join-Path $Root "itam_portal.spec")

$execDir = Join-Path $Root "exec"
New-Item -ItemType Directory -Force -Path $execDir | Out-Null
$exeOut = Join-Path $execDir "ITAM_Portal.exe"
Copy-Item -Force (Join-Path $Root "dist\ITAM_Portal.exe") $exeOut
# GitHub web "Describe this release" rejects .exe; Release *binaries* accept exe, but ZIP always works for uploads.
$zipOut = Join-Path $execDir "ITAM_Portal.zip"
if (Test-Path $zipOut) { Remove-Item -Force $zipOut }
Compress-Archive -LiteralPath $exeOut -DestinationPath $zipOut -CompressionLevel Optimal
$db = Join-Path $Root "db.sqlite3"
if (Test-Path $db) {
    Copy-Item -Force $db (Join-Path $execDir "db.sqlite3")
} else {
    Write-Warning "db.sqlite3 not found in repo root; exec folder has exe only."
}
Write-Host "Done: $exeOut"
Write-Host "      $zipOut (use this ZIP on GitHub if the web UI rejects .exe)"
