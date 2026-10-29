param([string]$CollectorRoot = 'D:\GITHUB\P_config')
$ErrorActionPreference = 'Stop'
$miniRoot = Split-Path -Parent $PSScriptRoot
$miniRunner = Join-Path $PSScriptRoot 'run_bridge.pyw'
$miniLocal = Join-Path $miniRoot '.local'
foreach ($miniRequired in @($miniRunner, (Join-Path $CollectorRoot '.venv\Scripts\pythonw.exe'), (Join-Path $CollectorRoot '.venv\Scripts\python.exe'), (Join-Path $CollectorRoot 'tools\codex_bridge.py'))) {
    if (-not (Test-Path -LiteralPath $miniRequired)) { throw ('Missing file: ' + $miniRequired) }
}
New-Item -ItemType Directory -Path $miniLocal -Force | Out-Null
$miniBackup = Join-Path $miniLocal ('steel-task-before-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.xml')
Export-ScheduledTask -TaskName MiniPI-CodexBridge | Set-Content -LiteralPath $miniBackup -Encoding UTF8
$miniAction = New-ScheduledTaskAction -Execute (Join-Path $CollectorRoot '.venv\Scripts\pythonw.exe') -Argument ('"' + $miniRunner + '" --collector-root "' + $CollectorRoot + '" --log-path "' + (Join-Path $miniLocal 'steel-bridge-run.jsonl') + '"') -WorkingDirectory $CollectorRoot
Set-ScheduledTask -TaskName MiniPI-CodexBridge -Action $miniAction -ErrorAction Stop | Select-Object TaskName,State
$miniVerifiedAction = (Get-ScheduledTask -TaskName MiniPI-CodexBridge -ErrorAction Stop).Actions
if ($miniVerifiedAction.Execute -ne $miniAction.Execute -or $miniVerifiedAction.Arguments -ne $miniAction.Arguments) {
    throw 'The scheduled action did not change.'
}
Write-Host 'Action repaired; existing schedule and pairing preserved. Wait for the next scheduled run.'
Get-ScheduledTaskInfo -TaskName MiniPI-CodexBridge | Format-List LastRunTime,LastTaskResult,NextRunTime
