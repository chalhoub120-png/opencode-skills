# Downloads deepseek-r1:14b main blob with resumable curl -C - (ollama pull truncates -partial and restarts from zero).
# Run detached for long runs so it survives server restart: Start-Process -WindowStyle Hidden powershell -File .\retry-pull.ps1
$model = "deepseek-r1:14b"
$digest = "6e9f90f02bb3b39b59e81916e8cfce9deb45aeaeb9a54a5be4414486b907dc1e"
$expected = [long]8988109952
$registryUrl = "https://registry.ollama.ai/v2/library/deepseek-r1/blobs/sha256:$digest"
$dest = Join-Path $env:USERPROFILE ".ollama\models\blobs\sha256-$digest"
$log = Join-Path $PSScriptRoot "retry-pull.log"

function Write-Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

function Measure-Allocated($path) {
    if (!(Test-Path $path)) { return [long]0 }
    $len = (Get-Item $path).Length
    if ($len -eq 0) { return [long]0 }
    $out = & fsutil file queryallocranges offset=0 length=$len "$path" 2>&1
    $sum = [long]0
    foreach ($l in $out) {
        if ($l -match 'Length:\s*0x([0-9a-fA-F]+)') {
            $sum += [Convert]::ToInt64($Matches[1], 16)
        }
    }
    return $sum
}

# Single-instance guard: never run two curl downloads of same blob at once.
$others = Get-CimInstance Win32_Process -Filter "Name='curl.exe'" |
    Where-Object { $_.CommandLine -match [regex]::Escape($digest) }
if ($others) {
    Write-Log "curl download of $digest already running (PID $($others.ProcessId -join ',')), exiting"
    exit 0
}

$attempt = 0
$delay = 15
while ($true) {
    $attempt++
    $before = Measure-Allocated $dest
    Write-Log "attempt #${attempt}: curl -C - resume allocated=${before}B expected=${expected}B"
    & curl.exe -L -C - --retry 5 --retry-delay 10 -o $dest $registryUrl
    $code = $LASTEXITCODE
    $after = Measure-Allocated $dest
    $len = if (Test-Path $dest) { (Get-Item $dest).Length } else { 0 }
    Write-Log "curl exit=$code allocated=${after}B length=${len}B"
    if ($code -eq 0 -and $len -eq $expected) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dest).Hash.ToLowerInvariant()
        if ($hash -eq $digest) {
            Write-Log "blob digest OK"
            ollama pull $model
            if ((ollama list) -match [regex]::Escape($model)) {
                Write-Log "SUCCESS: $model installed"
                ollama list | Add-Content -Path $log -Encoding utf8
                break
            }
            Write-Log "ollama pull finished but model missing; continuing retries"
        } else {
            Write-Log "digest mismatch (got $hash); keeping file for inspection"
        }
    }
    Write-Log "failed, retry in ${delay}s (file kept for resume)"
    Start-Sleep -Seconds $delay
    $delay = [Math]::Min($delay * 2, 120)
}
