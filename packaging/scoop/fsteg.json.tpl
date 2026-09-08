{
  "version": "__VERSION__",
  "description": "High-fidelity FFT block-based frequency domain steganography CLI & library",
  "homepage": "https://github.com/Kishan-Agarwal-28/fsteg",
  "license": "MIT",
  "architecture": {
    "64bit": {
      "url": "https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v__VERSION__/fsteg-v__VERSION__-x86_64-pc-windows-msvc.zip",
      "hash": "__SHA256__"
    }
  },
  "bin": "fsteg.exe",
  "checkver": "github",
  "autoupdate": {
    "architecture": {
      "64bit": {
        "url": "https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v$version/fsteg-v$version-x86_64-pc-windows-msvc.zip"
      }
    }
  }
}
