# KI-Editing-Pack für Claude Code installieren (Windows)
$target = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $target | Out-Null
Get-ChildItem -Directory (Join-Path $PSScriptRoot "skills") | ForEach-Object {
  $dest = Join-Path $target $_.Name
  if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
  Copy-Item -Recurse $_.FullName $dest
}
$eng = Join-Path $env:USERPROFILE ".claude\ki-editing-engine"
if (Test-Path $eng) { Remove-Item -Recurse -Force $eng }
Copy-Item -Recurse (Join-Path $PSScriptRoot "ki-editing-engine") $eng
Write-Host "KI-Editing-Pack installiert nach $target - Claude Code neu starten, dann / tippen."
