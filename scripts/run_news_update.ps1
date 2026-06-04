$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Updater = Join-Path $Root "scripts\update_all_news.py"
$LogDir = Join-Path $Root "data"
$Log = Join-Path $LogDir "news-update.log"
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $Python) {
  exit 1
}

$DeepSeekKey = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "User")
$DeepSeekModel = [Environment]::GetEnvironmentVariable("DEEPSEEK_MODEL", "User")
if ($DeepSeekKey) { $env:DEEPSEEK_API_KEY = $DeepSeekKey }
if ($DeepSeekModel) { $env:DEEPSEEK_MODEL = $DeepSeekModel }

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
Push-Location $Root
try {
  & $Python $Updater *> $Log
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
