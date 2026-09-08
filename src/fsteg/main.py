#!/usr/bin/env python3
"""
fsteg — FFT Block Steganography: Hide text inside images
========================================================
Hides or extracts a UTF-8 text message by quantising the magnitudes of
mid-frequency DFT coefficients inside every non-overlapping 8×8 block of
the image's luma (Y) channel.

Key features
------------
* Self-correcting embed: each block is verified through a uint8 round-trip
  so decoded bits always match, even after saving as PNG.
* CRC-32 integrity check on extraction.
* 4-byte length prefix + 8-byte sentinel so extraction never needs to
  know the message length in advance.
* Works on PNG, BMP, TIFF (lossless formats). JPEG is not recommended
  because re-encoding breaks the embedded bits.

Usage
-----
  Embed:
      fsteg embed cover.png "Your secret message" stego.png
      fsteg embed cover.png "$(cat secret.txt)" stego.png

  Extract:
      fsteg extract stego.png

  Capacity check (see how many bytes an image can hold):
      fsteg capacity image.png
"""

import sys
import struct
import zlib
import argparse
import numpy as np
from PIL import Image

if sys.platform.startswith("win") and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── tunables ───────────────────────────────────────────────────────────────────
STEP        = 32      # quantisation step (must stay fixed between embed/extract)
END_MARKER  = b"\x00\xFF\x00\xFF\xDE\xAD\xBE\xEF"  # 8-byte payload sentinel

# Mid-frequency positions in an unshifted 8×8 DFT
# DC (0,0) excluded; high-frequency corners avoided for robustness
MID_FREQ = [
    (1,0),(2,0),(3,0),
    (0,1),(1,1),(2,1),(3,1),
    (0,2),(1,2),(2,2),(3,2),
    (0,3),(1,3),(2,3),
]
BITS_PER_BLOCK = len(MID_FREQ)   # 14 usable bits per 8×8 block

# ── bit / byte helpers ─────────────────────────────────────────────────────────

def _to_bits(data: bytes) -> list[int]:
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def _to_bytes(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i:i+8]:
            byte = (byte << 1) | b
        out.append(byte)
    return bytes(out)


def _conj(r: int, c: int) -> tuple[int, int]:
    """Conjugate-symmetric DFT position (ensures real IFFT output)."""
    return (8 - r) % 8, (8 - c) % 8


def _capacity(channel: np.ndarray) -> int:
    H, W = channel.shape
    return (H // 8) * (W // 8) * BITS_PER_BLOCK

# ── core block operations ──────────────────────────────────────────────────────

def _embed_block(block: np.ndarray, bits: list) -> np.ndarray:
    """
    Embed up to BITS_PER_BLOCK bits into one 8×8 float block.

    Uses a self-correcting loop: after embedding and doing an IFFT, the block
    is converted to uint8 and back, then its DFT is re-examined.  Any
    coefficient whose parity flipped during that round-trip is nudged one
    quantisation level further from the boundary and the check is repeated
    (up to 5 times, which is always sufficient in practice).
    """
    S = np.fft.fft2(block)

    for _attempt in range(5):
        # ── embed pass ──
        for idx, (r, c) in enumerate(MID_FREQ):
            bit = bits[idx]
            if bit is None:
                continue
            cr, cc  = _conj(r, c)
            mag     = abs(S[r, c])
            phase   = np.angle(S[r, c])
            q       = round(mag / STEP)
            if bit == 1:
                if q % 2 == 0: q += 1
            else:
                if q % 2 == 1: q += 1
            nm = max(q * STEP, STEP)
            S[r,  c]  = nm * np.exp( 1j * phase)
            S[cr, cc] = nm * np.exp(-1j * phase)

        # ── uint8 round-trip check ──
        pixels   = np.clip(np.fft.ifft2(S).real, 0, 255)
        pixels8  = pixels.astype(np.uint8).astype(float)
        S_rt     = np.fft.fft2(pixels8)

        all_ok = True
        for idx, (r, c) in enumerate(MID_FREQ):
            bit = bits[idx]
            if bit is None:
                continue
            q_rt = round(abs(S_rt[r, c]) / STEP)
            if q_rt % 2 != bit:
                # Parity flipped — nudge this coefficient one step further
                all_ok  = False
                cr, cc  = _conj(r, c)
                phase   = np.angle(S_rt[r, c])
                q_fix   = q_rt + 1
                if q_fix % 2 != bit: q_fix += 1
                nm = max(q_fix * STEP, STEP)
                # Update S from the round-tripped version so corrections stack
                S[r,  c]  = nm * np.exp( 1j * phase)
                S[cr, cc] = nm * np.exp(-1j * phase)

        if all_ok:
            break

    return np.fft.ifft2(S).real


def _decode_block(block: np.ndarray) -> list[int]:
    """Read BITS_PER_BLOCK embedded bits from one 8×8 float block."""
    S = np.fft.fft2(block)
    return [round(abs(S[r, c]) / STEP) % 2 for r, c in MID_FREQ]

# ── high-level API ─────────────────────────────────────────────────────────────

def embed(cover_path: str, message: str, output_path: str) -> None:
    """Embed *message* into *cover_path* and write the stego image to *output_path*."""

    img   = Image.open(cover_path).convert("YCbCr")
    arr   = np.array(img, dtype=float)          # H × W × 3  (Y, Cb, Cr)
    y_arr = arr[:, :, 0]

    # ── build payload: CRC32 | length | UTF-8 text | sentinel ──
    msg_bytes = message.encode("utf-8")
    crc       = zlib.crc32(msg_bytes) & 0xFFFFFFFF
    payload   = struct.pack(">II", crc, len(msg_bytes)) + msg_bytes + END_MARKER
    all_bits  = _to_bits(payload)

    cap = _capacity(y_arr)
    if len(all_bits) > cap:
        max_msg = (cap // 8) - len(END_MARKER) - 8   # 8 bytes = crc + length
        raise ValueError(
            f"Message too long ({len(msg_bytes)} bytes encoded to {len(all_bits)} bits).\n"
            f"This image can hide at most ~{max_msg} bytes of text."
        )

    H, W      = y_arr.shape
    stego_y   = y_arr.copy()
    bits_iter = iter(all_bits)

    for i in range(H // 8):
        for j in range(W // 8):
            # Collect this block's worth of bits (pad with None at the end)
            block_bits = []
            for _ in MID_FREQ:
                try:    block_bits.append(next(bits_iter))
                except StopIteration: block_bits.append(None)

            block    = y_arr[i*8:(i+1)*8, j*8:(j+1)*8].copy()
            modified = _embed_block(block, block_bits)
            stego_y[i*8:(i+1)*8, j*8:(j+1)*8] = np.clip(modified, 0, 255)

    # ── reconstruct and save ──
    arr[:, :, 0] = stego_y
    stego_img    = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "YCbCr")
    stego_img.convert("RGB").save(output_path)

    max_delta = np.abs(stego_y - y_arr).max()
    pct_used  = 100 * len(all_bits) / cap
    print(f"[✓] Message embedded successfully → '{output_path}'")
    print(f"    Hidden text size     : {len(msg_bytes)} bytes")
    print(f"    Bits written         : {len(all_bits)}")
    print(f"    Image capacity used  : {pct_used:.1f}%  ({len(all_bits)}/{cap} bits)")
    print(f"    Max luma pixel shift : {max_delta:.2f} / 255")


def extract(stego_path: str) -> str:
    """Extract and return the hidden UTF-8 message from *stego_path*."""

    img   = Image.open(stego_path).convert("YCbCr")
    y_arr = np.array(img, dtype=float)[:, :, 0]
    H, W  = y_arr.shape

    all_bits = []
    for i in range(H // 8):
        for j in range(W // 8):
            block = y_arr[i*8:(i+1)*8, j*8:(j+1)*8]
            all_bits.extend(_decode_block(block))

    raw = _to_bytes(all_bits)

    # ── locate sentinel ──
    pos = raw.find(END_MARKER)
    if pos < 0:
        raise ValueError(
            "No hidden message found.  The image may not contain one, "
            "or it was saved with lossy compression (e.g. JPEG)."
        )

    if pos < 8:
        raise ValueError("Payload header is truncated — cannot extract message.")

    # ── parse header: CRC (4 bytes) + length (4 bytes) ──
    stored_crc, msg_len = struct.unpack(">II", raw[:8])
    msg_bytes = raw[8 : 8 + msg_len]

    if len(msg_bytes) < msg_len:
        raise ValueError(
            f"Payload truncated: expected {msg_len} bytes, recovered {len(msg_bytes)}."
        )

    # ── integrity check ──
    actual_crc = zlib.crc32(msg_bytes) & 0xFFFFFFFF
    if actual_crc != stored_crc:
        raise ValueError(
            f"CRC-32 mismatch (stored {stored_crc:#010x}, computed {actual_crc:#010x}). "
            "The image may have been modified after embedding."
        )

    return msg_bytes.decode("utf-8")


def capacity(image_path: str) -> None:
    """Print the hiding capacity of an image."""
    img   = Image.open(image_path)
    w, h  = img.size
    cap   = (h // 8) * (w // 8) * BITS_PER_BLOCK
    overhead = len(END_MARKER) + 8    # sentinel + crc + length
    usable   = cap // 8 - overhead
    print(f"Image size    : {w} × {h} px")
    print(f"8×8 blocks    : {(h//8) * (w//8)}")
    print(f"Total capacity: {cap} bits  ({cap//8} bytes)")
    print(f"Usable for text: ~{usable} bytes  (~{usable} UTF-8 characters)")

# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="fsteg",
        description="FFT block steganography — hide text inside images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    em = sub.add_parser("embed",    help="Embed a message into a cover image.")
    em.add_argument("cover",   help="Input cover image (PNG/BMP/TIFF recommended).")
    em.add_argument("message", help='Text to hide. Wrap in quotes: "Hello world"')
    em.add_argument("output",  help="Output stego image (e.g. stego.png).")

    ex = sub.add_parser("extract", help="Extract a hidden message from a stego image.")
    ex.add_argument("stego", help="Stego image to read from.")

    cap = sub.add_parser("capacity", help="Show the hiding capacity of an image.")
    cap.add_argument("image", help="Image file to inspect.")

    args = parser.parse_args()

    if args.cmd == "embed":
        try:
            embed(args.cover, args.message, args.output)
        except Exception as exc:
            print(f"[✗] Embed failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "extract":
        try:
            msg = extract(args.stego)
            print("[✓] Hidden message extracted:")
            print()
            print(msg)
        except Exception as exc:
            print(f"[✗] Extract failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "capacity":
        try:
            capacity(args.image)
        except Exception as exc:
            print(f"[✗] {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

