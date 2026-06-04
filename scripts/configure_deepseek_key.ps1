$ErrorActionPreference = "Stop"

Write-Host "Paste your DeepSeek API key. It will be stored in the Windows user environment variable DEEPSEEK_API_KEY."
$SecureKey = Read-Host "DeepSeek API key" -AsSecureString
$Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)

try {
  $PlainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
  if ([string]::IsNullOrWhiteSpace($PlainKey)) {
    throw "API key is empty."
  }

  [Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", $PlainKey, "User")
  [Environment]::SetEnvironmentVariable("DEEPSEEK_MODEL", "deepseek-v4-pro", "User")
  Write-Host "DeepSeek configuration saved. Restart scheduled tasks or new terminals to pick up the user environment."
}
finally {
  if ($Bstr -ne [IntPtr]::Zero) {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
  }
}
