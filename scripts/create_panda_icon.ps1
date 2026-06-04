$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$AssetDir = Join-Path $Root "assets"
$IconPath = Join-Path $AssetDir "panda.ico"

New-Item -ItemType Directory -Force -Path $AssetDir | Out-Null

Add-Type -AssemblyName System.Drawing

$Bitmap = New-Object System.Drawing.Bitmap 256, 256
$Graphics = [System.Drawing.Graphics]::FromImage($Bitmap)
$Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$Graphics.Clear([System.Drawing.Color]::FromArgb(246, 248, 248))

$Black = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(31, 35, 38))
$White = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$Accent = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(23, 107, 135))

$Graphics.FillEllipse($Black, 35, 28, 70, 74)
$Graphics.FillEllipse($Black, 151, 28, 70, 74)
$Graphics.FillEllipse($White, 42, 42, 172, 168)
$Graphics.FillEllipse($Black, 66, 90, 50, 58)
$Graphics.FillEllipse($Black, 140, 90, 50, 58)
$Graphics.FillEllipse($White, 82, 107, 14, 16)
$Graphics.FillEllipse($White, 156, 107, 14, 16)
$Graphics.FillEllipse($Black, 112, 135, 32, 24)
$Graphics.FillPie($Black, 98, 138, 60, 48, 12, 156)
$Graphics.FillEllipse($Accent, 96, 188, 64, 18)

$Handle = $Bitmap.GetHicon()
$Icon = [System.Drawing.Icon]::FromHandle($Handle)
$Stream = [System.IO.File]::Open($IconPath, [System.IO.FileMode]::Create)
$Icon.Save($Stream)
$Stream.Close()

$Graphics.Dispose()
$Bitmap.Dispose()
$Icon.Dispose()

Write-Output $IconPath
