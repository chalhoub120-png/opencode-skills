# OpenCode Skill Guard — PowerShell 5.1 compatible
# Protects against: Prompt Injection via SKILL.md, and auto-update hijack via curl|bash / missing hashes.
# Keeps skills enabled but monitored. Default mode: read-only.

[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [Parameter()][string]$Root = 'C:\Users\user\.config\opencode\skills',
    [Parameter()][string]$ProjectRoot = '',
    [switch]$Quarantine,
    [switch]$Fix
)

$ErrorActionPreference = 'Stop'
$script:results = @()
$script:manifest = @{ version='1.0'; generated=(Get-Date).ToString('o'); skills=@() }

$patternPrompt = '(?i)ignore\s+(all\s+)?previous|system\s*(prompt|instruction)|override\s+instructions|jailbreak|DAN\s*mode|you\s+are\s+now|forget\s+everything|pretend\s+to\s+be'
$patternCurl   = '(?i)curl\s+.*\|\s*(bash|sh|zsh|pwsh)|wget\s+.*\|\s*(bash|sh|zsh|pwsh)|Invoke-WebRequest\s+.*\|\s*iex|Invoke-Expression\s*\('
$patternShell  = 'shell\s*=\s*True'
$patternSecret = '(?i)(api_key|secret_key|access_token|password|auth_token)\s*=\s*.{16,}'
$patternExec   = '(?i)eval\s*\(|exec\s*\(|os\.system\s*\(|popen\s*\('

function Test-Patterns {
    param([string]$Content, [string]$Pattern)
    return ($content -match $Pattern)
}

function Get-SkillHash {
    param([string]$Path)
    $bytes = Get-Content $Path -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($null -eq $bytes) { return 'UNREADABLE' }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($bytes))
    return [BitConverter]::ToString($hash).Replace('-','').ToLower()
}

function Process-Skill {
    param([string]$SkillDir, [string]$Source)
    $name = Split-Path $SkillDir -Leaf
    $skillMd = Join-Path $SkillDir 'SKILL.md'
    $record = [PSCustomObject]@{
        Name=$name; Source=$Source; Path=$SkillDir;
        Status='OK'; Risk='LOW'; Issues=@(); Hash=''; Action='none'
    }

    if (-not (Test-Path $skillMd)) {
        $record.Status='MISSING_SKILLMD'; $record.Risk='MEDIUM'
        $record.Issues += 'SKILL.md not found'
        $script:results += $record
        return
    }

    $content = Get-Content $skillMd -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) { $record.Status='UNREADABLE'; $record.Risk='HIGH'; $script:results += $record; return }

    if (Test-Patterns $content $patternPrompt) { $record.Issues += 'PromptInjection found in SKILL.md' }
    if (Test-Patterns $content $patternCurl)   { $record.Issues += 'CurlPipeBash found in SKILL.md' }
    if (Test-Patterns $content $patternShell)  { $record.Issues += 'ShellTrue found in SKILL.md' }
    if (Test-Patterns $content $patternSecret) { $record.Issues += 'HardcodedSecret found in SKILL.md' }
    if (Test-Patterns $content $patternExec)   { $record.Issues += 'RemoteCodeExec found in SKILL.md' }

    $files = Get-ChildItem $SkillDir -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\node_modules\\|\\\.venv|\\venv\\|\\__pycache__\\|\\\.git\\|\\dist\\|\\build\\|\\\.cache\\' -and $_.Length -lt 524288 }
    foreach ($f in $files) {
        try { $fc = Get-Content $f.FullName -Raw -ErrorAction Stop } catch { continue }
        if (Test-Patterns $fc $patternCurl)   { $record.Issues += "CurlPipeBash in $($f.Name)" }
        if (Test-Patterns $fc $patternShell)  { $record.Issues += "ShellTrue in $($f.Name)" }
        if (Test-Patterns $fc $patternSecret) { $record.Issues += "HardcodedSecret in $($f.Name)" }
        if (Test-Patterns $fc $patternExec)   { $record.Issues += "RemoteCodeExec in $($f.Name)" }
    }

    if ($record.Issues -contains 'PromptInjection found in SKILL.md') { $record.Risk='CRITICAL' }
    elseif ($record.Issues.Count -ge 3) { $record.Risk='HIGH' }
    elseif ($record.Issues.Count -gt 0) { $record.Risk='MEDIUM' }

    $record.Hash = Get-SkillHash $skillMd

    if ($record.Risk -in @('CRITICAL','HIGH')) {
        if ($Quarantine) {
            $record.Action = 'quarantine'
            $dest = Join-Path (Split-Path $SkillDir -Parent) '_quarantine' $name
            if ($Fix -and $PSCmdlet.ShouldProcess($SkillDir, "Move to quarantine")) {
                New-Item -ItemType Directory -Path (Join-Path (Split-Path $SkillDir -Parent) '_quarantine') -Force | Out-Null
                Move-Item -Path $SkillDir -Destination $dest -Force
                $record.Status = 'QUARANTINED'
            }
        } else {
            $record.Action = 'monitor_only'
            $record.Status = 'MONITOR'
        }
    } elseif ($record.Risk -eq 'MEDIUM') {
        $record.Action = 'review_before_use'
        $record.Status = 'REVIEW'
    }

    $script:manifest.skills += [PSCustomObject]@{
        Name=$name; Source=$Source; Hash=$record.Hash; Risk=$record.Risk; Status=$record.Status; Checked=(Get-Date).ToString('o')
    }
    $script:results += $record
}

function Write-Report {
    param([string]$OutPath)
    $report = [PSCustomObject]@{
        Generated=(Get-Date).ToString('o')
        Total=$script:results.Count
        Critical=($script:results | Where-Object {$_.Risk -eq 'CRITICAL'}).Count
        High=($script:results | Where-Object {$_.Risk -eq 'HIGH'}).Count
        Medium=($script:results | Where-Object {$_.Risk -eq 'MEDIUM'}).Count
        Low=($script:results | Where-Object {$_.Risk -eq 'LOW'}).Count
        Quarantined=($script:results | Where-Object {$_.Status -eq 'QUARANTINED'}).Count
        Monitor=($script:results | Where-Object {$_.Status -eq 'MONITOR'}).Count
        Results=$script:results
        Manifest=$script:manifest
    }
    $report | ConvertTo-Json -Depth 4 | Out-File -FilePath $OutPath -Encoding UTF8
    return $report
}

Write-Host "=== OpenCode Skill Guard ===" -ForegroundColor Cyan
Write-Host "Global root: $Root"
if ($ProjectRoot) { Write-Host "Project root: $ProjectRoot" }

$allDirs = @()
if (Test-Path $Root) {
    $allDirs += Get-ChildItem $Root -Directory -ErrorAction SilentlyContinue | Select-Object FullName
}
if ($ProjectRoot -and (Test-Path $ProjectRoot)) {
    $allDirs += Get-ChildItem $ProjectRoot -Directory -ErrorAction SilentlyContinue | Select-Object FullName
}
Write-Host "Total skills found: $($allDirs.Count)"

foreach ($d in $allDirs) {
    $src = if ($d.FullName -like '*\.config\opencode\skills*') { 'global' } else { 'project' }
    Process-Skill -SkillDir $d.FullName -Source $src
}

$reportPath = Join-Path (Get-Location) 'skill-guard-report.json'
$report = Write-Report -OutPath $reportPath

Write-Host "`n=== Scan Result ===" -ForegroundColor Cyan
Write-Host "Total: $($report.Total) | CRITICAL: $($report.Critical) | HIGH: $($report.High) | MEDIUM: $($report.Medium) | LOW: $($report.Low)"
Write-Host "Quarantined: $($report.Quarantined) | Monitor: $($report.Monitor)"
Write-Host "Detailed report: $reportPath"

$manifestPath = Join-Path (Get-Location) 'skill-manifest.json'
$script:manifest | ConvertTo-Json -Depth 4 | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Host "Manifest saved to: $manifestPath"
Write-Host "To detect future skill changes, compare current SKILL.md hashes against this manifest."
