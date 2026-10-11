#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Create Azure Student free App Service and zip-deploy MoC (SPA + FastAPI).

.NOTES
  Prerequisites:
    - az login
    - Neo4j Aura env vars set in this shell (or passed as params)
    - OPENAI_API_KEY set in this shell
#>
param(
  [string]$ResourceGroup = "rg-moc-platform",
  [string]$Location = "swedencentral",
  [string]$AppName = "moc-intel-student",
  [string]$PlanName = "plan-moc-platform",
  [string]$Sku = "B1",
  [string]$Neo4jUri = $env:NEO4J_URI,
  [string]$Neo4jUser = $(if ($env:NEO4J_USER) { $env:NEO4J_USER } else { $env:NEO4J_USERNAME }),
  [string]$Neo4jPassword = $env:NEO4J_PASSWORD,
  [string]$OpenAiKey = $env:OPENAI_API_KEY
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Require([string]$Name, [string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value)) {
    throw "Missing required value: $Name. Set env var or pass -parameter."
  }
}

function AzOk {
  return ($LASTEXITCODE -eq 0)
}

Write-Host "==> Checking Azure CLI login..."
az account show 1>$null 2>$null
if (-not (AzOk)) {
  Write-Host "Not logged in. Opening az login..."
  az login
  if (-not (AzOk)) { throw "az login failed" }
}

Require "NEO4J_URI" $Neo4jUri
Require "NEO4J_USER / NEO4J_USERNAME" $Neo4jUser
Require "NEO4J_PASSWORD" $Neo4jPassword
Require "OPENAI_API_KEY" $OpenAiKey

Write-Host "==> Building frontend..."
Push-Location (Join-Path $Root "frontend")
npm run build
if (-not (AzOk)) { Pop-Location; throw "frontend build failed" }
Pop-Location

Write-Host "==> Ensuring resource group $ResourceGroup in $Location..."
az group create --name $ResourceGroup --location $Location | Out-Null
if (-not (AzOk)) { throw "Failed to create resource group" }

Write-Host "==> Creating App Service plan $PlanName ($Sku)..."
az appservice plan show --name $PlanName --resource-group $ResourceGroup 1>$null 2>$null
if (-not (AzOk)) {
  az appservice plan create `
    --name $PlanName `
    --resource-group $ResourceGroup `
    --sku $Sku `
    --is-linux | Out-Null
  if (-not (AzOk)) { throw "Failed to create App Service plan (try -Sku B1 or -Location westeurope)" }
}

Write-Host "==> Creating web app $AppName..."
az webapp show --name $AppName --resource-group $ResourceGroup 1>$null 2>$null
if (-not (AzOk)) {
  az webapp create `
    --resource-group $ResourceGroup `
    --plan $PlanName `
    --name $AppName `
    --runtime "PYTHON:3.11" | Out-Null
  if (-not (AzOk)) { throw "Failed to create web app" }
}

Write-Host "==> Configuring app settings..."
az webapp config appsettings set `
  --resource-group $ResourceGroup `
  --name $AppName `
  --settings `
    NEO4J_URI="$Neo4jUri" `
    NEO4J_USER="$Neo4jUser" `
    NEO4J_PASSWORD="$Neo4jPassword" `
    OPENAI_API_KEY="$OpenAiKey" `
    OPENAI_MODEL="gpt-4o" `
    SCM_DO_BUILD_DURING_DEPLOYMENT="true" `
    WEBSITES_PORT="8000" `
    FRONTEND_DIST="/home/site/wwwroot/frontend/dist" `
    CHROMA_PERSIST_DIR="/home/site/wwwroot/chroma_db" `
    MODEL_DIR="/home/site/wwwroot/saved_models" `
    CORS_ORIGINS="https://$AppName.azurewebsites.net" | Out-Null

az webapp config set `
  --resource-group $ResourceGroup `
  --name $AppName `
  --startup-file "startup.sh" | Out-Null

Write-Host "==> Creating deploy zip..."
$ZipPath = Join-Path $Root "deploy.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

$include = @(
  "api",
  "core",
  "modules",
  "frontend\dist",
  "saved_models",
  "chroma_db",
  "startup.sh"
)

$staging = Join-Path $env:TEMP "moc-deploy-staging"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

foreach ($item in $include) {
  $src = Join-Path $Root $item
  if (-not (Test-Path $src)) {
    Write-Warning "Skipping missing path: $item"
    continue
  }
  $dest = Join-Path $staging $item
  $destParent = Split-Path $dest -Parent
  if (-not (Test-Path $destParent)) { New-Item -ItemType Directory -Path $destParent -Force | Out-Null }
  Copy-Item -Path $src -Destination $dest -Recurse -Force
}

# Prefer slim Azure requirements for Oryx install time
$azureReq = Join-Path $Root "requirements-azure.txt"
$reqDest = Join-Path $staging "requirements.txt"
if (Test-Path $azureReq) {
  Copy-Item $azureReq $reqDest -Force
} else {
  Copy-Item (Join-Path $Root "requirements.txt") $reqDest -Force
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $ZipPath -Force

Write-Host "==> Zip deploying to $AppName..."
az webapp config set `
  --resource-group $ResourceGroup `
  --name $AppName `
  --startup-file "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000" | Out-Null

az webapp deployment source config-zip `
  --resource-group $ResourceGroup `
  --name $AppName `
  --src $ZipPath `
  --timeout 1800
if (-not (AzOk)) { throw "Zip deploy / remote build failed — check Kudu logs" }

$url = "https://$AppName.azurewebsites.net"
Write-Host ""
Write-Host "Deployed: $url"
Write-Host "Health:   $url/api/health"
Write-Host "Resource group: $ResourceGroup  App: $AppName"
Write-Host $url
