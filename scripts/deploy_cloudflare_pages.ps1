$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "This project uses Cloudflare Workers Static Assets now."
Write-Host "Forwarding to scripts\deploy_cloudflare_worker.ps1 ..."

& (Join-Path $Root "scripts\deploy_cloudflare_worker.ps1")

