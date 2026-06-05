$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $env:CLOUDFLARE_API_TOKEN) {
  $UserToken = [Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "User")
  if ($UserToken) {
    $env:CLOUDFLARE_API_TOKEN = $UserToken
  }
}

if (-not $env:CLOUDFLARE_ACCOUNT_ID) {
  $UserAccountId = [Environment]::GetEnvironmentVariable("CLOUDFLARE_ACCOUNT_ID", "User")
  if ($UserAccountId) {
    $env:CLOUDFLARE_ACCOUNT_ID = $UserAccountId
  }
}

if (-not $env:CLOUDFLARE_API_TOKEN) {
  Write-Error "CLOUDFLARE_API_TOKEN is not set. Run scripts\configure_cloudflare_api.ps1 first."
}

Push-Location $Root
try {
  npm run build
  npx --yes wrangler deploy
}
finally {
  Pop-Location
}

