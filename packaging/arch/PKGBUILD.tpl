# Maintainer: Kishan Agarwal <kishanagarwal028@gmail.com>
pkgname=fsteg-bin
pkgver=__VERSION__
pkgrel=1
pkgdesc="High-fidelity FFT block-based frequency domain steganography CLI"
arch=('x86_64' 'aarch64')
url="https://github.com/Kishan-Agarwal-28/fsteg"
license=('MIT')
provides=('fsteg')
conflicts=('fsteg')

source_x86_64=("https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v${pkgver}/fsteg-v${pkgver}-x86_64-unknown-linux-gnu.tar.gz")
sha256sums_x86_64=('__X86_64_SHA__')

source_aarch64=("https://github.com/Kishan-Agarwal-28/fsteg/releases/download/v${pkgver}/fsteg-v${pkgver}-aarch64-unknown-linux-gnu.tar.gz")
sha256sums_aarch64=('__AARCH64_SHA__')

package() {
    install -Dm755 "${srcdir}/fsteg" "${pkgdir}/usr/bin/fsteg"
    install -Dm644 "${srcdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE" || true
    install -Dm644 "${srcdir}/README.md" "${pkgdir}/usr/share/doc/${pkgname}/README.md" || true
}
