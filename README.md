# 🛰️ fsteg — FFT Block-Based Frequency Domain Steganography

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Fast Fourier Transform](https://img.shields.io/badge/Algorithm-2D--FFT%20%2F%20DFT-orange.svg)](https://en.wikipedia.org/wiki/Discrete_Fourier_transform)
[![Integrity Validation](https://img.shields.io/badge/Integrity-CRC--32-green.svg)](https://en.wikipedia.org/wiki/Cyclic_redundancy_check)
[![Package Manager](https://img.shields.io/badge/uv-compatible-purple.svg?logo=astral)](https://github.com/astral-sh/uv)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

A high-fidelity, frequency-domain steganography engine in Python. **`fsteg`** embeds arbitrary UTF-8 text messages inside digital images by quantising the magnitude spectrum of mid-frequency Discrete Fourier Transform (DFT) coefficients across non-overlapping $8 \times 8$ blocks of the image's luma ($Y$) channel.

Unlike naive spatial-domain steganography (such as LSB substitution) which can be trivially detected via statistical histograms or chi-squared attacks, `fsteg` distributes the secret signal across orthogonal 2D sinusoidal basis functions. It features an adaptive **self-correcting round-trip verification engine** that resolves spatial discretization and clipping errors, ensuring 100% bit recovery upon extraction.

---

## 📑 Table of Contents

- [Motivation & Comparison](#-motivation--comparison)
- [Key Features](#-key-features)
- [System Architecture & Theory](#-system-architecture--theory)
  - [1. YCbCr Luma Channel Isolation](#1-ycbcr-luma-channel-isolation)
  - [2. 8×8 Block Tiling & 2D Discrete Fourier Transform](#2-88-block-tiling--2d-discrete-fourier-transform)
  - [3. Mid-Frequency Coefficient Selection](#3-mid-frequency-coefficient-selection)
  - [4. Hermitian (Conjugate) Symmetry Enforcement](#4-hermitian-conjugate-symmetry-enforcement)
  - [5. Quantization Index Modulation (QIM)](#5-quantization-index-modulation-qim)
  - [6. The Self-Correcting uint8 Round-Trip Loop](#6-the-self-correcting-uint8-round-trip-loop)
- [Protocol & Binary Framing](#-protocol--binary-framing)
- [Payload Capacity & Sizing Guide](#-payload-capacity--sizing-guide)
- [Installation & Setup](#-installation--setup)
- [CLI Reference & Usage](#-cli-reference--usage)
  - [Check Capacity](#1-check-image-capacity)
  - [Embed Message](#2-embed-a-message)
  - [Extract Message](#3-extract-a-hidden-message)
- [Programmatic Python API](#-programmatic-python-api)
- [Lossless vs. Lossy Carrier Formats](#-lossless-vs-lossy-carrier-formats)
- [Security & Operational Best Practices](#-security--operational-best-practices)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)
- [Project Layout](#-project-layout)
- [License](#-license)

---

## 💡 Motivation & Comparison

| Characteristic | Spatial LSB Substitution | Frequency-Domain (`fsteg` FFT) |
| :--- | :--- | :--- |
| **Embedding Domain** | Spatial pixel intensity bitplanes | 2D Fourier magnitude spectrum |
| **Perceptual Invisibility** | High in high-noise regions; poor in smooth gradients | Outstanding across all image regions |
| **Statistical Steganalysis** | Vulnerable to Chi-Square, RS analysis, and Sample Pair Analysis | Resilient to spatial histogram and pixel-difference steganalysis |
| **Energy Distribution** | Confined to individual pixels | Dispersed over entire $8 \times 8$ spatial block |
| **Bit-Discretization Handling** | Trivial (direct integer manipulation) | **Self-correcting iterative feedback loop** |
| **Integrity Assurance** | Often none (raw bit insertion) | Built-in **CRC-32 checksum** with length header & sentinel |

---

## ✨ Key Features

- **Adaptive Self-Correction**: When floating-point Inverse FFT values are clipped to $[0, 255]$ and discretized to `uint8`, quantization noise can invert frequency coefficient parities. `fsteg` simulates this round-trip on each block up to 5 times, iteratively nudging coefficients away from decision boundaries until convergence is achieved.
- **Hermitian Conjugate Symmetry Preservation**: Automatically mirrors spectral modifications to conjugate coordinates $(8-r, 8-c)$, guaranteeing that the inverse transform remains strictly real-valued without imaginary artifacts.
- **Mid-Frequency Band Allocation**: Exactly 14 bits embedded per $8 \times 8$ block. Low-frequency DC $(0,0)$ is preserved to avoid perceptual shifts in luminance, and extreme high-frequency corners are avoided for stability.
- **Blind Extraction**: Embeds a 4-byte big-endian message length prefix and an 8-byte hexadecimal end marker (`0x00FF00FFDEADBEEF`), eliminating the need for the receiver to know payload length beforehand.
- **Tamper Detection via CRC-32**: Automatically computes and verifies an IEEE 802.3 32-bit CRC. Extraction aborts with an informative diagnostic error if the payload was modified or corrupted.

---

## 🔬 System Architecture & Theory

```
[ Cover Image ] ──────► Convert to YCbCr ──────► Extract Y Channel (Luma)
                                                         │
                                               Partition into 8×8 Blocks
                                                         │
[ Secret Message ]                                       ▼
        │                              ┌───────────────────────────────────┐
Compute CRC-32 + Pack Length Prefix    │ For each 8×8 block:               │
        │                              │  1. Compute 2D FFT: S = FFT2(B)   │
        ▼                              │  2. Quantize 14 mid-freq coefs    │
[ Payload Stream + 8-Byte Sentinel ] ─►│  3. Enforce conjugate symmetry    │
                                       │  4. Run self-correcting IFFT loop │
                                       └───────────────────────────────────┘
                                                         │
                                              Reassemble Stego Y Channel
                                                         │
[ Stego Image ] ◄────── Convert to RGB ◄──────── Merge Y with original Cb, Cr
```

### 1. YCbCr Luma Channel Isolation
The human visual system (HVS) possesses significantly greater sensitivity to variations in luminance than to chromaticity (color difference). `fsteg` transforms the input cover image from RGB to YCbCr:

$$Y = 0.299\,R + 0.587\,G + 0.114\,B$$

The embedding logic is applied **exclusively to the $Y$ (luma) channel**, while $Cb$ and $Cr$ remain unchanged, minimizing perceptible color cast.

### 2. 8×8 Block Tiling & 2D Discrete Fourier Transform
The luminance plane $Y$ is tiled into non-overlapping blocks $B_{i, j}$ of dimension $8 \times 8$ pixels ($0 \le m, n \le 7$). The 2D Discrete Fourier Transform converts each spatial block into its 2D spectral components:

$$S[u, v] = \sum_{m=0}^{7} \sum_{n=0}^{7} B[m, n] \cdot e^{-j 2\pi \left( \frac{um}{8} + \frac{vn}{8} \right)}$$

Each complex coefficient $S[u, v]$ possesses a magnitude $M = |S[u, v]|$ and phase $\phi = \arg(S[u, v])$.

### 3. Mid-Frequency Coefficient Selection
Each $8 \times 8$ block holds exactly **14 usable bits**. The coordinates selected in the unshifted DFT matrix are:

```
        v ->   0      1      2      3      4      5      6      7
   u +------------------------------------------------------------
   0 |        DC    bit3   bit7  bit11     .      .      .      .
   1 |      bit0    bit4   bit8  bit12     .      .      .      .
   2 |      bit1    bit5   bit9  bit13     .      .      .      .
   3 |      bit2    bit6  bit10     .      .      .      .      .
   4 |         .       .      .     .      .      .      .      .
   5 |         .       .      .     .      .      .      .      .
   6 |         .       .      .     .      .      .      .      .
   7 |         .       .      .     .      .      .      .      .
```

- **DC component $(0, 0)$ is omitted**: Modifying DC alters the average block brightness, leading to blocky artifacts.
- **High frequencies are omitted**: High frequencies carry little energy and are vulnerable to mild spatial perturbations.
- **Selected coordinates**: `(1,0), (2,0), (3,0), (0,1), (1,1), (2,1), (3,1), (0,2), (1,2), (2,2), (3,2), (0,3), (1,3), (2,3)`.

### 4. Hermitian (Conjugate) Symmetry Enforcement
Because spatial pixel values are real numbers, their Fourier transform must satisfy Hermitian symmetry:

$$S[(8 - u) \pmod 8, (8 - v) \pmod 8] = S^*[u, v]$$

Whenever the magnitude at $(u, v)$ is altered, `fsteg` calculates the conjugate coordinate $(u^*, v^*) = ((8-u)\%8, (8-v)\%8)$ and assigns:

$$S[u, v] = M_{\text{new}} \cdot e^{j \phi}, \qquad S[u^*, v^*] = M_{\text{new}} \cdot e^{-j \phi}$$

This prevents the Inverse FFT from producing non-zero imaginary residuals.

### 5. Quantization Index Modulation (QIM)
A uniform quantizer with step size $\Delta = 32$ is applied to coefficient magnitudes:

$$q = \text{round}\left(\frac{|S[u, v]|}{\Delta}\right)$$

Data bits are encoded into the **parity** of the quantization integer $q$:
- **Bit 1**: $q$ must be **odd** ($q \pmod 2 = 1$). If even, $q \leftarrow q + 1$.
- **Bit 0**: $q$ must be **even** ($q \pmod 2 = 0$). If odd, $q \leftarrow q + 1$.

The modulated magnitude is computed as $M' = \max(q \cdot \Delta, \Delta)$, preserving original phase $\phi$.

### 6. The Self-Correcting uint8 Round-Trip Loop
A common point of failure in frequency-domain steganography is the conversion back to the spatial integer domain:

$$\text{pixels} = \text{clip}\left(\text{Re}(\text{IFFT2}(S)), 0, 255\right) \xrightarrow{\text{round}} \text{uint8}$$

Quantization to 8-bit integers and edge clipping introduces broadband spatial noise $e[m, n]$. When taking $\text{FFT2}(\text{pixels}_{\text{uint8}})$, the reconstructed magnitude $M_{\text{rt}}$ may shift across the decision boundary:

$$\text{round}\left(\frac{M_{\text{rt}}}{\Delta}\right) \pmod 2 \neq \text{embedded bit}$$

To solve this, `fsteg` implements an **iterative self-correction feedback loop** in `_embed_block()`:
1. Synthesizes spatial block via `ifft2` and converts to `uint8`.
2. Computes `fft2` on the quantized `uint8` block to check the recovered parity.
3. For any coefficient where parity flipped, nudges the quantization level $q_{\text{fix}}$ further away from the decision boundary.
4. Updates the spectral matrix and repeats (converges in 1–2 iterations, guaranteed within 5 passes).

---

## 📦 Protocol & Binary Framing

The binary payload is structured with strict network big-endian serialization:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       CRC-32 (4 Bytes)                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Payload Length L (4 Bytes)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                    Payload Data (L Bytes)                     +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+              Sentinel (8 Bytes: 0x00FF00FFDEADBEEF)           +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **CRC-32** (4 bytes, `uint32_t`, big-endian): Verifies payload authenticity.
- **Length $L$** (4 bytes, `uint32_t`, big-endian): Byte length of the UTF-8 text string.
- **Payload** ($L$ bytes): Raw UTF-8 encoded text.
- **Sentinel** (8 bytes): `\x00\xFF\x00\xFF\xDE\xAD\xBE\xEF` used to demarcate end of payload during streaming extraction.
- **Fixed Framing Overhead**: $4 + 4 + 8 = 16\text{ bytes}$ ($128\text{ bits}$).

---

## 📊 Payload Capacity & Sizing Guide

The maximum data that can be embedded in an image depends strictly on its pixel dimensions:

$$\text{Capacity}_{\text{raw}} = \left\lfloor\frac{H}{8}\right\rfloor \times \left\lfloor\frac{W}{8}\right\rfloor \times 14\text{ bits}$$

$$\text{Capacity}_{\text{usable}} \approx \left\lfloor\frac{\text{Capacity}_{\text{raw}}}{8}\right\rfloor - 16\text{ bytes}$$

### Reference Table

| Resolution | Dimensions ($W \times H$) | $8 \times 8$ Blocks | Raw Capacity (Bits) | Usable Capacity (Bytes) | Typical Payload Fit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Small Avatar** | $256 \times 256$ | $1,024$ | $14,336$ | **$1,776$ B** | Small paragraphs, private keys |
| **Standard** | $512 \times 512$ | $4,096$ | $57,344$ | **$7,152$ B** | Multi-page text, code snippets |
| **HD 720p** | $1280 \times 720$ | $14,400$ | $201,600$ | **$25,184$ B** | Short articles, scripts |
| **Full HD 1080p** | $1920 \times 1080$ | $32,400$ | $453,600$ | **$56,684$ B** | Complete document / chapter |
| **CTF Sample** | $2500 \times 1343$ | $52,104$ | $729,456$ | **$91,166$ B** | Comprehensive archive, book chapter |
| **4K UHD** | $3840 \times 2160$ | $129,600$ | $1,814,400$ | **$226,784$ B** | Medium-length novella |

---

---

## 🚀 Installation & Setup

### ⚡ One-Line Standalone Install (No Python Required)

#### Linux & macOS:
```bash
curl -fsSL https://raw.githubusercontent.com/Kishan-Agarwal-28/fsteg/main/scripts/install.sh | bash
```

#### Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/Kishan-Agarwal-28/fsteg/main/scripts/install.ps1 | iex
```

---

### 📦 System Package Managers

#### Python Package Index (PyPI):
```bash
pip install fsteg
# or via uv:
uv tool install fsteg
```

#### Homebrew (macOS & Linux):
```bash
brew tap Kishan-Agarwal-28/tap
brew install fsteg
```

#### Chocolatey (Windows):
```powershell
choco install fsteg
```

#### Scoop (Windows):
```powershell
scoop install https://github.com/Kishan-Agarwal-28/fsteg/releases/latest/download/fsteg.json
```

#### Windows Package Manager (WinGet):
```powershell
winget install fsteg
```

#### Debian / Ubuntu (APT):
```bash
# Download latest .deb from GitHub Releases
curl -LO https://github.com/Kishan-Agarwal-28/fsteg/releases/latest/download/fsteg_amd64.deb
sudo dpkg -i fsteg_amd64.deb
```

#### Arch Linux (AUR / Pacman):
```bash
# Using makepkg from release PKGBUILD:
curl -LO https://github.com/Kishan-Agarwal-28/fsteg/releases/latest/download/PKGBUILD
makepkg -si
```

---

### 🛠️ Developer Setup (from source)

#### Using `uv`:
```bash
git clone https://github.com/Kishan-Agarwal-28/fsteg.git
cd fsteg
uv sync
uv run fsteg --help
```

#### Using `pip` and `venv`:
```bash
git clone https://github.com/Kishan-Agarwal-28/fsteg.git
cd fsteg
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -e .
```

---

## 💻 CLI Reference & Usage

`main.py` provides a clean command-line interface with three primary subcommands:

```
usage: main.py [-h] {embed,extract,capacity} ...
```

### 1. Check Image Capacity
Determine the exact number of bytes a carrier image can accommodate before attempting to embed:

```bash
# Usage: python main.py capacity <image_path>
python main.py capacity cover.png
```

**Example Output:**
```text
Image size    : 1920 × 1080 px
8×8 blocks    : 32400
Total capacity: 453600 bits  (56700 bytes)
Usable for text: ~56684 bytes  (~56684 UTF-8 characters)
```

---

### 2. Embed a Message
Embed a string or file content into a cover image and write the resulting stego image.

#### Single-line string:
```bash
# Usage: python main.py embed <cover_image> "<message>" <output_image>
python main.py embed cover.png "Project Titan: Launch window confirmed for 0400 UTC." stego.png
```

#### Multi-line text or file contents:
```bash
# Linux / macOS (Bash):
python main.py embed cover.png "$(cat classified_brief.txt)" stego.png

# Windows (PowerShell):
python main.py embed cover.png (Get-Content -Raw classified_brief.txt) stego.png
```

**Example Output:**
```text
[✓] Message embedded successfully → 'stego.png'
    Hidden text size     : 48 bytes
    Bits written         : 512
    Image capacity used  : 0.1%  (512/453600 bits)
    Max luma pixel shift : 2.84 / 255
```

---

### 3. Extract a Hidden Message
Recover and verify the concealed payload from a stego image:

```bash
# Usage: python main.py extract <stego_image>
python main.py extract stego.png
```

**Example Output:**
```text
[✓] Hidden message extracted:

Project Titan: Launch window confirmed for 0400 UTC.
```

---

## 🐍 Programmatic Python API

You can also import `fsteg` as a module directly inside your Python projects or automated scripts:

```python
from main import embed, extract, capacity

# 1. Inspect image hiding headroom
capacity("carrier.png")

# 2. Embed secret data
secret_message = "Confidential coordinates: 37.7749° N, 122.4194° W"
embed(
    cover_path="carrier.png",
    message=secret_message,
    output_path="carrier_stego.png"
)

# 3. Extract and verify data
recovered = extract("carrier_stego.png")
print("Recovered Message:", recovered)
assert recovered == secret_message
```

---

## 🖼️ Lossless vs. Lossy Carrier Formats

> [!IMPORTANT]
> Always use **lossless image formats** such as **PNG**, **BMP**, or **TIFF** for `fsteg`.

### Why JPEG Re-Encoding Fails
Standard JPEG compression operates by partitioning images into $8 \times 8$ blocks, computing the Discrete Cosine Transform (DCT), and dividing by a lossy quantization table:

$$C_{\text{quantized}}[u, v] = \text{round}\left(\frac{C_{\text{DCT}}[u, v]}{Q[u, v]}\right)$$

This step discards subtle high- and mid-frequency fluctuations to minimize file size. This lossy quantization corrupts the precise DFT magnitude parities established by `fsteg`, resulting in CRC mismatch or an undetectable sentinel. 

*(Note: If a JPEG carrier is saved at uncompressed/maximum 100% quality settings, the data may occasionally survive, but PNG/BMP/TIFF are strongly recommended for guaranteed fidelity.)*

---

## 🛡️ Security & Operational Best Practices

1. **Steganography vs. Cryptography**:
   - Steganography hides the *existence* of communication.
   - Cryptography protects the *confidentiality* of the content.
   - **Recommendation**: Always encrypt your message prior to embedding (e.g., using AES-GCM or ChaCha20-Poly1305). If intercepted, an adversary inspecting spectral coefficients will extract only ciphertext.
2. **Visual Fidelity**:
   - `STEP = 32` yields an average pixel shift $\Delta_{\text{pixel}} \approx 1\text{ to }3$ intensity levels out of $255$. This remains completely imperceptible to human inspection.
3. **Carrier Selection**:
   - Select cover images with rich natural textures (landscapes, urban photography, textured surfaces) rather than artificial flat color backgrounds. Natural texture energy in the frequency spectrum provides superior camouflage.

---

## 🔧 Troubleshooting & FAQs

### Q: UnicodeEncodeError: `'charmap' codec can't encode character '\u2713'` (Windows PowerShell / CMD)
**Cause:** Windows command terminals often default to legacy code pages (e.g., `cp1252`).  
**Fix:** Force UTF-8 encoding in Python before running:
```powershell
$env:PYTHONIOENCODING="utf-8"
python main.py extract stego.png
```
Or switch console code page: `chcp 65001`.

---

### Q: `ValueError: Message too long (...)`
**Cause:** The message byte size exceeds the image's capacity.  
**Fix:** Run `python main.py capacity <image>` to check the limits. Use a higher-resolution cover image or compress the payload (e.g., `gzip`) before embedding.

---

### Q: `ValueError: No hidden message found`
**Cause:** The 8-byte sentinel marker was not found in the decoded bitstream.  
**Common reasons:**
- The image was converted or re-saved using lossy compression (JPEG, WebP).
- The image was cropped, resized, rotated, or color-adjusted.
- The image does not contain an `fsteg` payload.

---

### Q: `ValueError: CRC-32 mismatch (stored 0x..., computed 0x...)`
**Cause:** The sentinel was discovered, but one or more bits in the payload were flipped.  
**Common reasons:**
- Minor spatial alterations, noise injection, or compression artifacts occurred after embedding.

---

## 📂 Project Layout

```text
fft-steg/
├── .gitignore             # Standard Python / uv gitignore rules
├── .python-version        # Locked Python interpreter version (3.11+)
├── pyproject.toml         # PEP 518/621 project metadata & dependencies
├── uv.lock                # Deterministic dependency lockfile
├── main.py                # Core steganography engine & CLI entrypoint
├── stego.jpg              # Sample carrier image
└── README.md              # Project documentation
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
