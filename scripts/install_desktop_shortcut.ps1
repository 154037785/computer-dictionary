$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$IconScript = Join-Path $Root "scripts\create_panda_icon.ps1"
$StartScript = Join-Path $Root "scripts\start_dictionary.ps1"
$IconPath = Join-Path $Root "assets\panda.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Computer Dictionary Panda.lnk"

if (-not (Test-Path $IconPath)) {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $IconScript | Out-Null
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$Shortcut.WorkingDirectory = $Root
$Shortcut.IconLocation = "$IconPath,0"
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Open the computer dictionary website and start the local server"
$Shortcut.Save()

Write-Output $ShortcutPath
