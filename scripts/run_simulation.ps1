param(
    [Parameter(Mandatory = $true)][string]$ProtocolPath,
    [Parameter(Mandatory = $true)][string]$LogPath,
    [string]$SimulatorPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$protocol = (Resolve-Path -LiteralPath $ProtocolPath).Path
$log = [System.IO.Path]::GetFullPath($LogPath)
$logDirectory = Split-Path -Parent $log
if ($logDirectory) { New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null }

$candidates = @()
if ($SimulatorPath) { $candidates += $SimulatorPath }
if ($env:AUTO_FLEX_SIMULATOR) { $candidates += $env:AUTO_FLEX_SIMULATOR }
$command = Get-Command opentrons_simulate -ErrorAction SilentlyContinue
if ($command) { $candidates += $command.Source }
$userProfile = [Environment]::GetFolderPath('UserProfile')
$candidates += (Join-Path $userProfile '.codex\venvs\auto-flex\Scripts\opentrons_simulate.exe')

$simulator = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
if (-not $simulator) {
    $message = 'opentrons_simulate was not found. Run scripts/setup_simulator.ps1, then retry.'
    [System.IO.File]::WriteAllText($log, $message, [System.Text.UTF8Encoding]::new($false))
    Write-Error $message
    exit 127
}

$ErrorActionPreference = 'Continue'
$output = & $simulator $protocol 2>&1
$exitCode = $LASTEXITCODE
$rendered = ($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
[System.IO.File]::WriteAllText($log, $rendered + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
$output | Write-Output
exit $exitCode
