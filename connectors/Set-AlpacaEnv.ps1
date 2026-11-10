# Stores Alpaca PAPER credentials as Windows user environment variables.
# Secrets are typed into a hidden prompt: they never appear in the console,
# in chat, in shell history, or in opencode.json.
#
# Usage:  powershell -ExecutionPolicy Bypass -File .\connectors\Set-AlpacaEnv.ps1

$ErrorActionPreference = "Stop"

function ConvertFrom-Secure {
    param([Security.SecureString] $Secret)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

Write-Host "Alpaca PAPER trading credentials" -ForegroundColor Cyan
Write-Host "Get them at: https://app.alpaca.markets/paper/dashboard/overview -> API Keys" -ForegroundColor DarkGray
Write-Host ""

$keyId = Read-Host "API Key ID (hidden)" -AsSecureString
$secret = Read-Host "Secret Key (hidden)" -AsSecureString

$keyIdPlain = ConvertFrom-Secure $keyId
$secretPlain = ConvertFrom-Secure $secret

if ([string]::IsNullOrWhiteSpace($keyIdPlain) -or [string]::IsNullOrWhiteSpace($secretPlain)) {
    throw "Empty value received. Nothing was written."
}

if ($secretPlain.Length -lt 20 -or $keyIdPlain.Length -lt 8) {
    throw "Value looks too short for an Alpaca key pair. Nothing was written."
}

if ([Environment]::GetEnvironmentVariable("ALPACA_API_KEY", "User") -ne $null) {
    $answer = Read-Host "ALPACA_API_KEY already exists. Overwrite? (y/N)"
    if ($answer -notin @("y", "Y", "yes")) {
        Write-Host "Aborted. Nothing was written." -ForegroundColor Yellow
        return
    }
}

[Environment]::SetEnvironmentVariable("ALPACA_API_KEY", $keyIdPlain, "User")
[Environment]::SetEnvironmentVariable("ALPACA_SECRET_KEY", $secretPlain, "User")
[Environment]::SetEnvironmentVariable("ALPACA_PAPER_TRADE", "true", "User")
[Environment]::SetEnvironmentVariable("ALPACA_TOOLSETS", "account,trading,stock-data", "User")

$keyIdPlain = $null
$secretPlain = $null
[GC]::Collect()

Write-Host ""
Write-Host "Stored ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER_TRADE=true, ALPACA_TOOLSETS." -ForegroundColor Green
Write-Host "Restart OpenCode so the new environment variables are picked up." -ForegroundColor Yellow
Write-Host "To switch to live trading later, set ALPACA_PAPER_TRADE=false yourself - the skill will warn you." -ForegroundColor DarkGray
