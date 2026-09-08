$ErrorActionPreference = 'Stop'

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url        = '__URL__'
$checksum   = '__SHA256__'

$packageArgs = @{
  packageName   = 'fsteg'
  unzipLocation = $toolsDir
  url64bit      = $url
  checksum64    = $checksum
  checksumType64= 'sha256'
}

Install-ChocolateyZipPackage @packageArgs
