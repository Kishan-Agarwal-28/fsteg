#!/usr/bin/env bash
# Universal installer for fsteg (Linux & macOS)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Kishan-Agarwal-28/fsteg/main/scripts/install.sh | bash

set -euo pipefail

REPO="Kishan-Agarwal-28/fsteg"
BIN_NAME="fsteg"

# Detect OS
OS="$(uname -s)"
case "${OS}" in
  Linux*)  OS_TARGET="unknown-linux-gnu" ;;
  Darwin*) OS_TARGET="apple-darwin" ;;
  *)
    echo "[-] Unsupported operating system: ${OS}"
    echo "    On Windows, install via PowerShell:"
    echo "    irm https://raw.githubusercontent.com/${REPO}/main/scripts/install.ps1 | iex"
    exit 1
    ;;
esac

# Detect Architecture
ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64|amd64) ARCH_TARGET="x86_64" ;;
  arm64|aarch64) ARCH_TARGET="aarch64" ;;
  *)
    echo "[-] Unsupported architecture: ${ARCH}"
    exit 1
    ;;
esac

TARGET="${ARCH_TARGET}-${OS_TARGET}"

# Determine version
if [ -z "${VERSION:-}" ]; then
  echo "[*] Fetching latest release tag for ${REPO}..."
  TAG=$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
  if [ -z "${TAG}" ]; then
    echo "[-] Failed to fetch latest release tag. Specify VERSION=vX.Y.Z explicitly."
    exit 1
  fi
else
  TAG="${VERSION}"
fi

ARCHIVE="${BIN_NAME}-${TAG}-${TARGET}.tar.gz"
URL="https://github.com/${REPO}/releases/download/${TAG}/${ARCHIVE}"
CHECKSUM_URL="${URL}.sha256"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "[*] Downloading ${BIN_NAME} ${TAG} for ${TARGET}..."
curl -sSL "${URL}" -o "${TMP_DIR}/${ARCHIVE}"
curl -sSL "${CHECKSUM_URL}" -o "${TMP_DIR}/${ARCHIVE}.sha256" || true

# Verify checksum if sha256 file exists and contains a valid hash
if [ -s "${TMP_DIR}/${ARCHIVE}.sha256" ]; then
  EXPECTED_SHA=$(awk '{print $1}' "${TMP_DIR}/${ARCHIVE}.sha256")
  if command -v sha256sum &>/dev/null; then
    ACTUAL_SHA=$(sha256sum "${TMP_DIR}/${ARCHIVE}" | awk '{print $1}')
  else
    ACTUAL_SHA=$(shasum -a 256 "${TMP_DIR}/${ARCHIVE}" | awk '{print $1}')
  fi

  if [ "${EXPECTED_SHA}" != "${ACTUAL_SHA}" ]; then
    echo "[-] SHA-256 verification failed!"
    echo "    Expected: ${EXPECTED_SHA}"
    echo "    Actual:   ${ACTUAL_SHA}"
    exit 1
  fi
  echo "[✓] SHA-256 integrity verified."
fi

# Extract
tar -xzf "${TMP_DIR}/${ARCHIVE}" -C "${TMP_DIR}"

# Determine install location
INSTALL_DIR="/usr/local/bin"
USE_SUDO=false

if [ ! -w "${INSTALL_DIR}" ]; then
  if command -v sudo &>/dev/null && [ -t 0 ]; then
    USE_SUDO=true
  else
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "${INSTALL_DIR}"
  fi
fi

echo "[*] Installing to ${INSTALL_DIR}/${BIN_NAME}..."
if [ "${USE_SUDO}" = true ]; then
  sudo install -m 755 "${TMP_DIR}/${BIN_NAME}" "${INSTALL_DIR}/${BIN_NAME}"
else
  install -m 755 "${TMP_DIR}/${BIN_NAME}" "${INSTALL_DIR}/${BIN_NAME}"
fi

echo "[✓] fsteg installed successfully!"
echo ""
"${INSTALL_DIR}/${BIN_NAME}" --help | head -n 8 || true

# Check PATH
case ":${PATH}:" in
  *:"${INSTALL_DIR}":*) ;;
  *)
    echo ""
    echo "[!] Warning: ${INSTALL_DIR} is not in your \$PATH."
    echo "    Add it to your profile:"
    echo "    export PATH=\"${INSTALL_DIR}:\$PATH\""
    ;;
esac
