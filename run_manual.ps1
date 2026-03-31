$ErrorActionPreference = 'Stop'
$project = 'C:\Users\Administrator\Documents\Playground\Trend_OB_AI'
Set-Location $project
$env:TELEGRAM_TARGET = '8205845992'
$env:USE_TOP_MARKETCAP_UNIVERSE = '1'
$env:TOP_MARKETCAP_COUNT = '100'
$env:ALERT_ONLY_WHEN_SIGNAL = '1'
$env:ALERT_REQUIRE_ALIGNMENT = '1'
$env:USE_LONGPORT = '1'
python run_system.py
