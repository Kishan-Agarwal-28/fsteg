$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$exePath  = Join-Path $toolsDir "fsteg.exe"

if (Test-Path $exePath) {
  Remove-Item $exePath -Force -ErrorAction SilentlyContinue
}
