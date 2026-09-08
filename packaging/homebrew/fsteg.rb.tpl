class Fsteg < Formula
  desc "High-fidelity FFT block-based frequency domain steganography CLI & library"
  homepage "https://github.com/Kishan-Agarwal-28/fsteg"
  version "__VERSION__"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v__VERSION__/fsteg-v__VERSION__-aarch64-apple-darwin.tar.gz"
      sha256 "__ARM64_DARWIN_SHA256__"
    else
      url "https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v__VERSION__/fsteg-v__VERSION__-x86_64-apple-darwin.tar.gz"
      sha256 "__X86_64_DARWIN_SHA256__"
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url "https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v__VERSION__/fsteg-v__VERSION__-aarch64-unknown-linux-gnu.tar.gz"
      sha256 "__AARCH64_LINUX_SHA256__"
    else
      url "https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v__VERSION__/fsteg-v__VERSION__-x86_64-unknown-linux-gnu.tar.gz"
      sha256 "__X86_64_LINUX_SHA256__"
    end
  end

  def install
    bin.install "fsteg"
  end

  test do
    system "#{bin}/fsteg", "--help"
  end
end
