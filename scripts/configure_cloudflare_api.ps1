$ErrorActionPreference = "Stop"

Write-Host "Cloudflare API setup" -ForegroundColor Cyan
Write-Host "Do not paste the token into chat. Paste it here; PowerShell will hide it."
Write-Host ""

$SecureToken = Read-Host "Paste Cloudflare API Token" -AsSecureString
$Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
try {
  $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
}
finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
}

if (-not $Token -or $Token.Trim().Length -lt 20) {
  Write-Error "Token looks too short. Setup cancelled."
}

$AccountId = Read-Host "Cloudflare Account ID (optional; press Enter to skip)"

[Environment]::SetEnvironmentVariable("CLOUDFLARE_API_TOKEN", $Token.Trim(), "User")
$env:CLOUDFLARE_API_TOKEN = $Token.Trim()

if ($AccountId.Trim()) {
  [Environment]::SetEnvironmentVariable("CLOUDFLARE_ACCOUNT_ID", $AccountId.Trim(), "User")
  $env:CLOUDFLARE_ACCOUNT_ID = $AccountId.Trim()
}

Write-Host ""
Write-Host "Saved CLOUDFLARE_API_TOKEN for the current Windows user." -ForegroundColor Green
if ($AccountId.Trim()) {
  Write-Host "Saved CLOUDFLARE_ACCOUNT_ID for the current Windows user." -ForegroundColor Green
}
Write-Host "Next step: run scripts\deploy_cloudflare_worker.ps1"

