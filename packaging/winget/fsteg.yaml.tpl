PackageIdentifier: fsteg
PackageVersion: __VERSION__
PackageName: fsteg
Publisher: Kishan Agarwal
License: MIT
LicenseUrl: https://github.com/Kishan-Agarwal-28/fsteg/blob/main/LICENSE
ShortDescription: High-fidelity FFT block-based frequency domain steganography CLI & library
PackageUrl: https://github.com/Kishan-Agarwal-28/fsteg
Commands:
  - fsteg
Installers:
  - Architecture: x64
    InstallerType: zip
    NestedInstallerType: portable
    NestedInstallerFiles:
      - RelativeFilePath: fsteg.exe
        PortableCommandAlias: fsteg
    InstallerUrl: https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v__VERSION__/fsteg-v__VERSION__-x86_64-pc-windows-msvc.zip
    InstallerSha256: __SHA256__
ManifestType: singleton
ManifestVersion: 1.6.0
