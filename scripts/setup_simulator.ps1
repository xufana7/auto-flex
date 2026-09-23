param(
    [string]$PythonPath,
    [string]$EnvironmentPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$userProfile = [Environment]::GetFolderPath('UserProfile')
if (-not $EnvironmentPath) { $EnvironmentPath = Join-Path $userProfile '.codex\venvs\auto-flex' }
$existingVenvPython = Join-Path $EnvironmentPath 'Scripts\python.exe'

if (Test-Path -LiteralPath $existingVenvPython -PathType Leaf) {
    & $existingVenvPython -m pip install --disable-pip-version-check opentrons
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install or update the opentrons package.' }
    $existingSimulator = Join-Path $EnvironmentPath 'Scripts\opentrons_simulate.exe'
    if (-not (Test-Path -LiteralPath $existingSimulator)) { throw 'The environment exists but opentrons_simulate.exe was not found.' }
    Write-Output $existingSimulator
    exit 0
}

if (-not $PythonPath) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($requestedVersion in @('3.12', '3.11')) {
            $candidate = & $launcher.Source "-$requestedVersion" -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path -LiteralPath $candidate.Trim() -PathType Leaf)) {
                $PythonPath = $candidate.Trim()
                break
            }
        }
    }
    if (-not $PythonPath) {
        foreach ($commandName in @('python3.12', 'python3.11', 'python')) {
            $command = Get-Command $commandName -ErrorAction SilentlyContinue
            if (-not $command) { continue }
            $candidateVersionParts = & $command.Source -c 'import sys; print(sys.version_info.major, sys.version_info.minor)'
            $candidateVersion = $candidateVersionParts.Trim() -replace '\s+', '.'
            if ($candidateVersion -in @('3.11', '3.12')) {
                $PythonPath = $command.Source
                break
            }
        }
    }
}
if (-not $PythonPath -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw 'Python 3.11 or 3.12 is required. Pass its executable with -PythonPath.'
}

$versionParts = & $PythonPath -c 'import sys; print(sys.version_info.major, sys.version_info.minor)'
$version = $versionParts.Trim() -replace '\s+', '.'
if ($version -notin @('3.11', '3.12')) {
    throw "Unsupported Python $version. Use Python 3.11 or 3.12 for the Opentrons simulator."
}

if (-not (Test-Path -LiteralPath $EnvironmentPath)) {
    & $PythonPath -m venv $EnvironmentPath
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create simulator virtual environment.' }
}
$venvPython = Join-Path $EnvironmentPath 'Scripts\python.exe'
& $venvPython -m pip install --disable-pip-version-check opentrons
if ($LASTEXITCODE -ne 0) { throw 'Failed to install the opentrons package.' }
$simulator = Join-Path $EnvironmentPath 'Scripts\opentrons_simulate.exe'
if (-not (Test-Path -LiteralPath $simulator)) { throw 'Installation completed but opentrons_simulate.exe was not found.' }
Write-Output $simulator
