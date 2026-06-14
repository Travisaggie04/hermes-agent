# Canonical native-Windows test runner for hermes-agent.
#
# Mirrors scripts/run_tests.sh while using the Windows virtualenv layout and a
# repo-local temp directory so pytest never depends on %LOCALAPPDATA%\Temp ACLs.

$ErrorActionPreference = "Stop"
$RunnerArgs = $args

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

$pythonCandidates = @(
    (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
    (Join-Path $RepoRoot "venv\Scripts\python.exe"),
    (Join-Path $env:USERPROFILE ".hermes\hermes-agent\venv\Scripts\python.exe"),
    (Join-Path $RepoRoot ".venv\bin\python"),
    (Join-Path $RepoRoot "venv\bin\python")
)

$Python = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        $Python = $candidate
        break
    }
}

if (-not $Python) {
    Write-Error "No virtualenv Python found in .venv or venv."
    exit 1
}

$TestTmp = Join-Path $RepoRoot ".codex-tmp\pytest"
New-Item -ItemType Directory -Force -Path $TestTmp | Out-Null

# Keep the child process hermetic enough for local/CI parity. PowerShell cannot
# do env -i directly, but environment mutations are scoped to this process and
# inherited only by the runner subprocess.
foreach ($name in @(Get-ChildItem Env: | ForEach-Object { $_.Name })) {
    if ($name -match "(?i)(API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|ACCESS_KEY|PRIVATE_KEY)") {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
}

$env:TMP = $TestTmp
$env:TEMP = $TestTmp
$env:TMPDIR = $TestTmp
$env:TZ = "UTC"
$env:LANG = "C.UTF-8"
$env:LC_ALL = "C.UTF-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONHASHSEED = "0"

if (Test-Path -LiteralPath (Join-Path $env:USERPROFILE ".hermes\pytest_live_guard.py")) {
    $env:PYTHONPATH = Join-Path $env:USERPROFILE ".hermes"
    $env:PYTEST_PLUGINS = "pytest_live_guard"
}

Write-Host "> running per-file parallel test suite via run_tests_parallel.py"
Write-Host "  (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0; repo-local temp)"

Set-Location $RepoRoot
& $Python (Join-Path $ScriptDir "run_tests_parallel.py") @RunnerArgs
exit $LASTEXITCODE
