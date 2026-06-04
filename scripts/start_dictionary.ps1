$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Port = 8765
$Refresh = [DateTimeOffset]::Now.ToUnixTimeSeconds()
$Url = "http://127.0.0.1:$Port/index.html?refresh=$Refresh"
$MobileUrlFile = Join-Path $Root "data\mobile-url.txt"
$NewsFile = Join-Path $Root "data\frontier-news.json"
$Updater = Join-Path $Root "scripts\update_frontier_news.py"
$WechatFile = Join-Path $Root "data\wechat-news.json"
$WechatUpdater = Join-Path $Root "scripts\update_wechat_posts.py"

function Get-LanIp {
  try {
    $Addresses = Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.InterfaceAlias -notmatch "VPN|vEthernet|Virtual|Loopback"
      }
    $Candidate = $Addresses |
      Where-Object { $_.PrefixOrigin -eq "Dhcp" } |
      Sort-Object InterfaceMetric |
      Select-Object -First 1
    if (-not $Candidate) {
      $Candidate = $Addresses |
        Sort-Object InterfaceMetric |
        Select-Object -First 1
    }
    if ($Candidate) { return $Candidate.IPAddress }
  } catch {
    return ""
  }
  return ""
}

function Test-PortOpen {
  param([int]$PortNumber)
  try {
    $Client = [System.Net.Sockets.TcpClient]::new()
    $Async = $Client.BeginConnect("127.0.0.1", $PortNumber, $null, $null)
    $Open = $Async.AsyncWaitHandle.WaitOne(300)
    if ($Open) { $Client.EndConnect($Async) }
    $Client.Close()
    return $Open
  } catch {
    return $false
  }
}

$ShouldUpdate = $true
if (Test-Path $NewsFile) {
  $Age = (Get-Date) - (Get-Item $NewsFile).LastWriteTime
  $ShouldUpdate = $Age.TotalHours -ge 12
}

if ($ShouldUpdate -and (Get-Command python -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath "python" -ArgumentList @($Updater) -WorkingDirectory $Root -WindowStyle Hidden
}

$ShouldUpdateWechat = $true
if (Test-Path $WechatFile) {
  $WechatAge = (Get-Date) - (Get-Item $WechatFile).LastWriteTime
  $ShouldUpdateWechat = $WechatAge.TotalHours -ge 12
}

if ($ShouldUpdateWechat -and (Get-Command python -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath "python" -ArgumentList @($WechatUpdater) -WorkingDirectory (Join-Path $Root "scripts") -WindowStyle Hidden
}

if (-not (Test-PortOpen -PortNumber $Port)) {
  if (Get-Command python -ErrorAction SilentlyContinue) {
    Start-Process -FilePath "python" -ArgumentList @("-m", "http.server", "$Port", "--bind", "0.0.0.0") -WorkingDirectory $Root -WindowStyle Hidden
    Start-Sleep -Milliseconds 800
  }
}

$LanIp = Get-LanIp
if ($LanIp) {
  $MobileUrl = "http://$LanIp`:$Port/index.html?refresh=$Refresh"
  Set-Content -Path $MobileUrlFile -Value $MobileUrl -Encoding UTF8
}

Start-Process $Url
