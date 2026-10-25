param(
    [ValidateRange(1,60)][int]$IntervalMinutes = 2,
    [switch]$UpdateExisting
)
$ErrorActionPreference = 'Stop'
$miniProjectRoot = Split-Path -Parent $PSScriptRoot
$miniTaskName = 'MiniPI-CodexBridge'
$miniExisting = Get-ScheduledTask -TaskName $miniTaskName -ErrorAction SilentlyContinue
$miniRepeat = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$miniDescription = "Mini PI: Codex maradék keretek küldése $IntervalMinutes percenként, modellhívás nélkül."
if ($miniExisting) {
    if (-not $UpdateExisting) { throw 'A MiniPI-CodexBridge feladat már létezik. Frissítéshez használd az -UpdateExisting kapcsolót.' }
    $miniOtherTriggers = @($miniExisting.Triggers | Where-Object { -not $_.Repetition.Interval })
    Set-ScheduledTask -TaskName $miniTaskName -Trigger (@($miniRepeat) + $miniOtherTriggers) | Out-Null
    $miniUpdated = Get-ScheduledTask -TaskName $miniTaskName
    $miniUpdated.Description = $miniDescription
    Set-ScheduledTask -InputObject $miniUpdated | Select-Object TaskName,State
    return
}
$miniPython = Join-Path $miniProjectRoot '.venv\Scripts\pythonw.exe'
$miniBridge = Join-Path $PSScriptRoot 'codex_bridge.py'
$miniArguments = '"' + $miniBridge + '"'
$miniAction = New-ScheduledTaskAction -Execute $miniPython -Argument $miniArguments -WorkingDirectory $miniProjectRoot
$miniLogon = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
$miniPrincipal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$miniSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $miniTaskName -Action $miniAction -Trigger @($miniRepeat,$miniLogon) -Principal $miniPrincipal -Settings $miniSettings -Description $miniDescription | Select-Object TaskName,State
