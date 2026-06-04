$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ProjectName = $env:CLOUDFLARE_PAGES_PROJECT
if (-not $ProjectName) {
  $ProjectName = "computer-dictionary"
}

if (-not $env:CLOUDFLARE_API_TOKEN) {
  Write-Error "CLOUDFLARE_API_TOKEN is not set. Create a Cloudflare API token and set it before deploying."
}

Push-Location $Root
try {
  npm run build
  npx --yes wrangler pages deploy public --project-name $ProjectName
}
finally {
  Pop-Location
}
