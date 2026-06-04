$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Port = 8765
$Refresh = [DateTimeOffset]::Now.ToUnixTimeSeconds()
$LocalUrl = "http://127.0.0.1:$Port/index.html?refresh=$Refresh"
$Cloudflared = Join-Path $Root "scripts\bin\cloudflared.exe"
$PublicUrlFile = Join-Path $Root "data\public-url.txt"
$LogDir = Join-Path $Root "data\tunnel-logs"
$OutLog = Join-Path $LogDir "cloudflared.out.log"
$ErrLog = Join-Path $LogDir "cloudflared.err.log"

function Test-PortOpen {
  param([string]$HostName, [int]$PortNumber)
  try {
    $Client = [System.Net.Sockets.TcpClient]::new()
    $Async = $Client.BeginConnect($HostName, $PortNumber, $null, $null)
    $Open = $Async.AsyncWaitHandle.WaitOne(500)
    if ($Open) { $Client.EndConnect($Async) }
    $Client.Close()
    return $Open
  } catch {
    return $false
  }
}

if (-not (Test-Path $Cloudflared)) {
  Set-Content -Path $PublicUrlFile -Value "cloudflared.exe was not found. Ask Codex to install the public tunnel tool first." -Encoding UTF8
  Start-Process notepad.exe $PublicUrlFile
  exit 1
}

if (-not (Test-PortOpen -HostName "127.0.0.1" -PortNumber $Port)) {
  if (Get-Command python -ErrorAction SilentlyContinue) {
    Start-Process -FilePath "python" -ArgumentList @("-m", "http.server", "$Port", "--bind", "0.0.0.0") -WorkingDirectory $Root -WindowStyle Hidden
    Start-Sleep -Seconds 2
  }
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Remove-Item -Path $OutLog, $ErrLog -Force -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "name='cloudflared.exe'" |
  Where-Object { $_.CommandLine -match "tunnel" -and $_.CommandLine -match "127\.0\.0\.1:$Port" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Process -FilePath $Cloudflared `
  -ArgumentList @("tunnel", "--url", "http://127.0.0.1:$Port", "--no-autoupdate") `
  -WorkingDirectory $Root `
  -WindowStyle Hidden `
  -RedirectStandardOutput $OutLog `
  -RedirectStandardError $ErrLog

$PublicUrl = ""
for ($i = 0; $i -lt 45; $i++) {
  Start-Sleep -Seconds 1
  $Combined = ""
  if (Test-Path $OutLog) { $Combined += Get-Content $OutLog -Raw -Encoding UTF8 }
  if (Test-Path $ErrLog) { $Combined += "`n" + (Get-Content $ErrLog -Raw -Encoding UTF8) }
  $Match = [regex]::Match($Combined, "https://[a-zA-Z0-9-]+\.trycloudflare\.com")
  if ($Match.Success) {
    $PublicUrl = "$($Match.Value)/index.html?refresh=$Refresh"
    break
  }
}

if ($PublicUrl) {
  Set-Content -Path $PublicUrlFile -Value $PublicUrl -Encoding UTF8
  Start-Process $PublicUrl
  Start-Process notepad.exe $PublicUrlFile
} else {
  Set-Content -Path $PublicUrlFile -Value "Failed to create a public URL. Check log: $ErrLog" -Encoding UTF8
  Start-Process notepad.exe $PublicUrlFile
  Start-Process $LocalUrl
}
