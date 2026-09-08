# Universal installer for fsteg on Windows PowerShell
# Usage:
#   irm https://raw.githubusercontent.com/Kishan-Agarwal-28/fsteg/main/scripts/install.ps1 | iex

$ErrorActionPreference = "Stop"

$Repo = "Kishan-Agarwal-28/fsteg"
$BinName = "fsteg.exe"
$Target = "x86_64-pc-windows-msvc"

Write-Host "[*] Fetching latest release tag for $Repo..." -ForegroundColor Cyan
$ReleaseApiUrl = "https://api.github.com/repos/$Repo/releases/latest"

try {
    $Release = Invoke-RestMethod -Uri $ReleaseApiUrl -UseBasicParsing
    $Tag = $Release.tag_name
} catch {
    Write-Error "[-] Failed to fetch latest release from GitHub API: $_"
    exit 1
}

$Archive = "fsteg-$Tag-$Target.zip"
$DownloadUrl = "https://github.com/$Repo/releases/download/$Tag/$Archive"
$ChecksumUrl = "$DownloadUrl.sha256"

$TempDir = Join-Path $env:TEMP ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
$ZipPath = Join-Path $TempDir $Archive
$ShaPath = Join-Path $TempDir "$Archive.sha256"

try {
    Write-Host "[*] Downloading fsteg $Tag ($Target)..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing

    try {
        Invoke-WebRequest -Uri $ChecksumUrl -OutFile $ShaPath -UseBasicParsing
        if (Test-Path $ShaPath) {
            $ExpectedSha = (Get-Content $ShaPath).Trim().Split()[0].ToLower()
            $ActualSha = (Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash.ToLower()
            if ($ExpectedSha -ne $ActualSha) {
                Write-Error "[-] SHA-256 verification failed! Expected: $ExpectedSha, Got: $ActualSha"
                exit 1
            }
            Write-Host "[✓] SHA-256 integrity verified." -ForegroundColor Green
        }
    } catch {
        Write-Warning "[!] Checksum file not found or could not be verified; continuing..."
    }

    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\fsteg\bin"
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

    Write-Host "[*] Extracting to $InstallDir..." -ForegroundColor Cyan
    Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force

    $SourceExe = Join-Path $TempDir "fsteg.exe"
    if (-not (Test-Path $SourceExe)) {
        # Check if inside a subfolder
        $Found = Get-ChildItem -Path $TempDir -Filter "fsteg.exe" -Recurse | Select-Object -First 1
        if ($Found) { $SourceExe = $Found.FullName }
    }

    Copy-Item -Path $SourceExe -Destination (Join-Path $InstallDir "fsteg.exe") -Force

    # Check and update PATH
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -notlike "*$InstallDir*") {
        Write-Host "[*] Adding $InstallDir to User PATH..." -ForegroundColor Cyan
        [Environment]::SetEnvironmentVariable("Path", "$InstallDir;$UserPath", "User")
        $env:Path = "$InstallDir;$env:Path"
    }

    Write-Host "[✓] fsteg installed successfully to: $InstallDir\fsteg.exe" -ForegroundColor Green
    Write-Host ""
    & "$InstallDir\fsteg.exe" --help
}
finally {
    Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
