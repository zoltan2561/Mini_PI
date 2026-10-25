param(
    [string]$CollectorRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$LogPath
)
$ErrorActionPreference = 'Stop'
if (-not $LogPath) { $LogPath = Join-Path $CollectorRoot '.local\bridge-run.jsonl' }
$miniExitCode = 1
$miniStarted = (Get-Date).ToString('o')
$miniFailure = $null
$miniConfigReadable = $null
try {
    # Console Python has valid stdout/stderr handles even in a hidden task.
    $miniOutput = & (Join-Path $CollectorRoot '.venv\Scripts\python.exe') (Join-Path $CollectorRoot 'tools\codex_bridge.py') 2>&1
    $miniExitCode = $LASTEXITCODE
    if ($null -eq $miniExitCode) { $miniExitCode = 1 }
    if ($miniExitCode -ne 0) {
        $miniFailure = 'BridgeError'
        if (($miniOutput | Out-String) -match '\b([A-Za-z]+Error)\b') { $miniFailure = $Matches[1] }
        try {
            $miniConfigStream = [System.IO.File]::OpenRead((Join-Path $CollectorRoot '.local\bridge-config.json'))
            $miniConfigStream.Dispose()
            $miniConfigReadable = $true
        } catch { $miniConfigReadable = $false }
    }
} catch {
    $miniExitCode = 1
    $miniFailure = $_.Exception.GetType().Name
}
try {
    # Only record status, never credentials or raw subprocess output.
    $miniRecord = [ordered]@{
        host = $env:COMPUTERNAME
        started_at = $miniStarted
        finished_at = (Get-Date).ToString('o')
        exit_code = $miniExitCode
        status = $(if ($miniExitCode -eq 0) { 'sent' } else { 'failed' })
        error_type = $miniFailure
        config_readable = $miniConfigReadable
    }
    $miniRecord | ConvertTo-Json -Compress | Add-Content -LiteralPath $LogPath -Encoding UTF8
} catch {
    # A logging or launch failure must never look like a successful send.
    $miniExitCode = 1
    Write-Error ('Mini PI runner: ' + $_.Exception.GetType().Name) -ErrorAction Continue
}
exit $miniExitCode
