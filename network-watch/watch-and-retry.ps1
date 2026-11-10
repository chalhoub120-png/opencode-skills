# Network watchdog: retry YouTube/Bilibili setup when the network becomes stable.
# Non-privileged. Safe to stop with Ctrl+C. Writes watch.log next to this script.

$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $here "watch.log"
$done = Join-Path $here "done.txt"
$env:UV_DEFAULT_INDEX = "https://mirrors.aliyun.com/pypi/simple/"
$env:UV_INDEX = "https://mirrors.aliyun.com/pypi/simple/"
$env:PIP_INDEX_URL = "https://mirrors.aliyun.com/pypi/simple/"
$agentReach = "$env:USERPROFILE\.local\bin\agent-reach.exe"
$interval = 300

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

Log "Watchdog started (interval ${interval}s). Press Ctrl+C to stop."
while (-not (Test-Path $done)) {
    $mirrors = @("mirrors.aliyun.com", "github.com", "files.pythonhosted.org")
    $ok = 0
    foreach ($host_ in $mirrors) {
        try {
            $tcp = Test-NetConnection -ComputerName $host_ -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
            if ($tcp) { $ok++ }
        } catch {}
    }
    Log "Probe: $ok/3 hosts reachable"
    if ($ok -ge 2) {
        Log "Network stable -> installing imageio-ffmpeg + agent-reach setup"
        python -m pip install --user --timeout 60 --retries 3 -i https://mirrors.aliyun.com/pypi/simple/ imageio-ffmpeg 2>&1 | Select-Object -Last 3 | ForEach-Object { Log $_ }
        $ver = (& $agentReach version 2>&1) -join " "
        Log "agent-reach version: $ver"
        & $agentReach setup 2>&1 | Select-Object -Last 5 | ForEach-Object { Log $_ }
        $report = "$env:USERPROFILE\.agent-reach\installation-report.md"
        if ((Test-Path $report) -and ((Get-Content $report -Encoding UTF8 -Raw) -match '5/5')) {
            Log "YouTube/Bilibili recovered (5/5)."
            New-Item -ItemType File -Path $done -Force | Out-Null
            Log "DONE. Safe to close the window."
            break
        }
        Log "Setup did not reach 5/5 - will retry next probe."
    }
    Start-Sleep -Seconds $interval
}
