param([string]$CollectorRoot = 'D:\GITHUB\P_config')
$ErrorActionPreference = 'Stop'
$miniRoot = Split-Path -Parent $PSScriptRoot
$miniRunner = Join-Path $PSScriptRoot 'run_bridge.ps1'
$miniLocal = Join-Path $miniRoot '.local'
foreach ($miniRequired in @($miniRunner, (Join-Path $CollectorRoot '.venv\Scripts\python.exe'), (Join-Path $CollectorRoot 'tools\codex_bridge.py'))) {
    if (-not (Test-Path -LiteralPath $miniRequired)) { throw ('Missing file: ' + $miniRequired) }
}
New-Item -ItemType Directory -Path $miniLocal -Force | Out-Null
$miniBackup = Join-Path $miniLocal ('steel-task-before-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.xml')
Export-ScheduledTask -TaskName MiniPI-CodexBridge | Set-Content -LiteralPath $miniBackup -Encoding UTF8
$miniAction = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $miniRunner + '" -CollectorRoot "' + $CollectorRoot + '" -LogPath "' + (Join-Path $miniLocal 'steel-bridge-run.jsonl') + '"') -WorkingDirectory $CollectorRoot
Set-ScheduledTask -TaskName MiniPI-CodexBridge -Action $miniAction | Select-Object TaskName,State
Write-Host 'Action repaired; existing schedule and pairing preserved. Wait for the next scheduled run.'
Get-ScheduledTaskInfo -TaskName MiniPI-CodexBridge | Format-List LastRunTime,LastTaskResult,NextRunTime
