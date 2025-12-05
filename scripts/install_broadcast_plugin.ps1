[CmdletBinding()]
param(
    [switch]$SkipDeploy,
    [string]$ComposeFile = "docker-compose.prod.yml",
    [string]$ServiceName = "cs2_modded_server"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ("==> {0}" -f $Message) -ForegroundColor Cyan
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$projectDir = Join-Path $repoRoot "counterstrikesharp\BroadcastCenter"
$pluginOutput = Join-Path $projectDir "bin\Release\net8.0\BroadcastCenterPlugin.dll"
$pluginsDir = Join-Path $repoRoot "cs2-data\game\csgo\addons\counterstrikesharp\plugins"
$targetDll = Join-Path $pluginsDir "BroadcastCenterPlugin.dll"
$composeFilePath = Join-Path $repoRoot $ComposeFile

if (-not (Test-Path $projectDir)) {
    throw "Cannot find plugin project directory at $projectDir"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is required to build the plugin."
}

$dockerImage = "mcr.microsoft.com/dotnet/sdk:8.0"
$buildArgs = @(
    "run", "--rm",
    "--volume", "$repoRoot:/src",
    "--workdir", "/src/counterstrikesharp/BroadcastCenter",
    $dockerImage,
    "dotnet", "build", "-c", "Release"
)

Write-Step "Building BroadcastCenterPlugin via $dockerImage"
& docker @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "dotnet build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $pluginOutput)) {
    throw "Build succeeded but $pluginOutput not found"
}

Write-Step "Copying plugin to $targetDll"
New-Item -ItemType Directory -Force -Path $pluginsDir | Out-Null
Copy-Item -Path $pluginOutput -Destination $targetDll -Force

if (-not $SkipDeploy) {
    if (-not (Test-Path $composeFilePath)) {
        throw "Compose file not found at $composeFilePath"
    }
    $composeArgs = @(
        "compose",
        "-f", $composeFilePath,
        "up", "-d", $ServiceName
    )
    Write-Step "Restarting $ServiceName using $ComposeFile"
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose command failed with exit code $LASTEXITCODE"
    }
}

Write-Step "Broadcast plugin installed successfully"
