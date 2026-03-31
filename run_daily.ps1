$ErrorActionPreference = 'Stop'
$project = 'C:\Users\Administrator\Documents\Playground\Trend_OB_AI'
$logDir = Join-Path $project 'logs'
if (-not (Test-Path $logDir)) { New-Item -Path $logDir -ItemType Directory | Out-Null }
$env:TELEGRAM_TARGET = '8205845992'
$env:USE_TOP_MARKETCAP_UNIVERSE = '1'
$env:TOP_MARKETCAP_COUNT = '100'
$env:ALERT_ONLY_WHEN_SIGNAL = '1'
$env:ALERT_REQUIRE_ALIGNMENT = '1'
$env:USE_LONGPORT = '1'
# Load LongPort credentials from User environment variables (avoid hardcoding secrets in repo)
$env:LONGPORT_APP_KEY = [Environment]::GetEnvironmentVariable('LONGPORT_APP_KEY', 'User')
$env:LONGPORT_APP_SECRET = [Environment]::GetEnvironmentVariable('LONGPORT_APP_SECRET', 'User')
$env:LONGPORT_ACCESS_TOKEN = [Environment]::GetEnvironmentVariable('LONGPORT_ACCESS_TOKEN', 'User')
Set-Location $project
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$logPath = Join-Path $logDir ("run-" + $ts + ".log")
python .\run_system.py *>&1 | Tee-Object -FilePath $logPath
