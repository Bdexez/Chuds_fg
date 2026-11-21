# Read-only loader check, with optional on-hardware runs of the two products.
# Run after register-layer.ps1 on a Windows machine with the Vulkan SDK.
[CmdletBinding()]
param(
    [string] $GameExe,
    [string[]] $GameArgs = @(),
    [string] $WindowTitle,
    [string] $VulkanInfo,
    [switch] $Wow6432
)
$ErrorActionPreference = 'Stop'

$name = if ($Wow6432) { 'VK_LAYER_CHUDS_fg_32' } else { 'VK_LAYER_CHUDS_fg' }
$registry = if ($Wow6432) {
    'HKCU:\SOFTWARE\WOW6432Node\Khronos\Vulkan\ImplicitLayers'
} else {
    'HKCU:\SOFTWARE\Khronos\Vulkan\ImplicitLayers'
}
if (-not (Test-Path $registry)) { throw "Layer registry key missing: $registry" }
$values = (Get-ItemProperty -Path $registry).PSObject.Properties.Name
if (-not ($values | Where-Object { $_ -like "*$name.json" })) {
    throw "Manifest for $name not registered under $registry"
}
Write-Host "Registry: $name found"

if (-not $VulkanInfo -and -not $Wow6432) {
    $VulkanInfo = (Get-Command vulkaninfo.exe -ErrorAction Stop).Source
}
if ($VulkanInfo) {
    $infoExe = (Resolve-Path -LiteralPath $VulkanInfo).Path
    $summary = (& $infoExe --summary 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "vulkaninfo failed: $summary" }
    if ($summary -notmatch [regex]::Escape($name)) {
        throw "$name absent from vulkaninfo --summary"
    }
    Write-Host "Vulkan loader: $name visible"
} else {
    Write-Host '32-bit loader check skipped; pass -VulkanInfo with a 32-bit vulkaninfo.exe to run it'
}

$capture = Join-Path $PSScriptRoot 'chuds_fg_capture.exe'
if (Test-Path $capture) {
    & $capture --list
    if ($LASTEXITCODE -ne 0) { throw 'chuds_fg_capture --list failed' }
    Write-Host 'Capture window enumeration: passed'
}

if ($GameExe) {
    $game = (Resolve-Path -LiteralPath $GameExe).Path
    $log = Join-Path $env:TEMP ("chuds-fg-layer-hardware-{0}.log" -f [guid]::NewGuid())
    $previousEnable = $env:CHUDS_FG
    $previousLog = $env:CHUDS_FG_LOG_FILE
    try {
        $env:CHUDS_FG = '1'
        $env:CHUDS_FG_LOG_FILE = $log
        Write-Host "Running Vulkan game: $game; layer log: $log"
        $launch = @{ FilePath = $game; Wait = $true; PassThru = $true }
        if ($GameArgs.Count -gt 0) { $launch.ArgumentList = $GameArgs }
        $gameProcess = Start-Process @launch
        if ($gameProcess.ExitCode -ne 0) {
            throw "Vulkan game exited with status $($gameProcess.ExitCode); inspect $log"
        }
    } finally {
        $env:CHUDS_FG = $previousEnable
        $env:CHUDS_FG_LOG_FILE = $previousLog
    }
    if (-not (Test-Path $log)) { throw "No layer log written at $log" }
    $layerLog = Get-Content -LiteralPath $log -Raw
    if ($layerLog -notmatch 'generation on') {
        throw "Layer loaded but generation was not confirmed. Inspect $log"
    }
    Write-Host 'Vulkan game: generation confirmed'
    Write-Host "Inspect $log for pacing, resize, HUD and validation errors."
}

if ($WindowTitle) {
    if (-not (Test-Path $capture)) { throw "Capture executable missing beside this script: $capture" }
    $log = Join-Path $env:TEMP ("chuds-fg-capture-hardware-{0}.log" -f [guid]::NewGuid())
    Write-Host "Capturing $WindowTitle; stop with Ctrl+Alt+Q; log: $log"
    & $capture --title $WindowTitle --mode extrapolate --multiplier 2 --hud 2 2>&1 |
        Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) { throw "Capture exited with status $LASTEXITCODE" }
    $captureLog = Get-Content -LiteralPath $log -Raw
    if ($captureLog -notmatch 'WGC dequeue -> synth submit') {
        throw "No capture/presentation latency sample. Inspect $log"
    }
    Write-Host 'Capture: frame and latency samples confirmed'
}
