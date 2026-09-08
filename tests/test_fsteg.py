"""
Test suite for fsteg (FFT Block Steganography).
Tests capacity inspection, embedding, extracting, error handling, and CLI functionality.
"""

import sys
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from fsteg.main import capacity, embed, extract, main, BITS_PER_BLOCK, END_MARKER


def create_sample_image(path: Path, width: int = 128, height: int = 128, fmt: str = "PNG") -> Path:
    """Generate a textured synthetic RGB test image."""
    x = np.linspace(30, 220, width, dtype=np.uint8)
    y = np.linspace(30, 220, height, dtype=np.uint8)
    xx, yy = np.meshgrid(x, y)
    r = xx
    g = yy
    b = ((xx.astype(int) + yy.astype(int)) // 2).astype(np.uint8)
    arr = np.stack([r, g, b], axis=-1)
    img = Image.fromarray(arr, mode="RGB")
    img.save(path, format=fmt)
    return path


class TestCapacity:
    """Tests for image hiding capacity calculations."""

    def test_capacity_output(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        img_path = create_sample_image(tmp_path / "test_cap.png", width=64, height=64)
        capacity(str(img_path))
        captured = capsys.readouterr().out

        expected_blocks = (64 // 8) * (64 // 8)
        expected_bits = expected_blocks * BITS_PER_BLOCK

        assert "Image size    : 64 × 64 px" in captured
        assert f"8×8 blocks    : {expected_blocks}" in captured
        assert f"Total capacity: {expected_bits} bits" in captured
        assert "Usable for text:" in captured


class TestEmbedExtract:
    """Tests for embedding and extracting messages."""

    def test_simple_ascii_roundtrip(self, tmp_path: Path):
        cover = create_sample_image(tmp_path / "cover.png", 128, 128)
        stego = tmp_path / "stego.png"
        secret = "Classified operational launch code: 987-ALPHA-OMEGA."

        embed(str(cover), secret, str(stego))
        assert stego.exists()

        extracted = extract(str(stego))
        assert extracted == secret

    def test_unicode_and_multiline_payload(self, tmp_path: Path):
        cover = create_sample_image(tmp_path / "cover_unicode.png", 128, 128)
        stego = tmp_path / "stego_unicode.png"
        secret = (
            "🛰️ Satellite Uplink: Active\n"
            "Lat/Long: 37.7749° N, 122.4194° W\n"
            "Special Chars: <Hello & World!> ~ ` ^ # @ % $ *"
        )

        embed(str(cover), secret, str(stego))
        extracted = extract(str(stego))
        assert extracted == secret

    def test_bmp_format_support(self, tmp_path: Path):
        cover = create_sample_image(tmp_path / "cover.bmp", 128, 128, fmt="BMP")
        stego = tmp_path / "stego.bmp"
        secret = "BMP lossless steganography test."

        embed(str(cover), secret, str(stego))
        extracted = extract(str(stego))
        assert extracted == secret

    def test_payload_too_large_raises_value_error(self, tmp_path: Path):
        # 16x16 image has only 4 blocks = 56 bits = 7 bytes total.
        # Overhead is 16 bytes, so usable capacity is 0 bytes.
        cover = create_sample_image(tmp_path / "tiny.png", 16, 16)
        stego = tmp_path / "tiny_stego.png"
        secret = "This message is far too long for a 16x16 image."

        with pytest.raises(ValueError, match="Message too long"):
            embed(str(cover), secret, str(stego))

    def test_extract_on_unembedded_image_raises_error(self, tmp_path: Path):
        cover = create_sample_image(tmp_path / "clean.png", 64, 64)

        with pytest.raises(ValueError, match="No hidden message found"):
            extract(str(cover))

    def test_tampered_image_detects_corruption(self, tmp_path: Path):
        cover = create_sample_image(tmp_path / "cover_tamper.png", 128, 128)
        stego = tmp_path / "stego_tamper.png"
        secret = "Integrity critical information."

        embed(str(cover), secret, str(stego))

        # Tamper with the stego image by altering pixel data
        img = Image.open(stego)
        arr = np.array(img)
        # Flip pixels in the first block
        arr[0:8, 0:8, :] = np.bitwise_xor(arr[0:8, 0:8, :], 0xAA)
        tampered_img = Image.fromarray(arr)
        tampered_img.save(stego)

        with pytest.raises(ValueError, match="(CRC-32 mismatch|No hidden message found)"):
            extract(str(stego))


class TestCLI:
    """Tests for the command-line interface."""

    def test_cli_capacity(self, tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch):
        cover = create_sample_image(tmp_path / "cli_cover.png", 64, 64)
        monkeypatch.setattr(sys, "argv", ["fsteg", "capacity", str(cover)])

        main()
        captured = capsys.readouterr().out
        assert "Image size    : 64 × 64 px" in captured
        assert "Total capacity:" in captured

    def test_cli_embed_and_extract(self, tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch):
        cover = create_sample_image(tmp_path / "cli_cover.png", 128, 128)
        stego = tmp_path / "cli_stego.png"
        secret = "CLI secret transmission."

        # Test embed via CLI
        monkeypatch.setattr(sys, "argv", ["fsteg", "embed", str(cover), secret, str(stego)])
        main()
        embed_output = capsys.readouterr().out
        assert "Message embedded successfully" in embed_output
        assert stego.exists()

        # Test extract via CLI
        monkeypatch.setattr(sys, "argv", ["fsteg", "extract", str(stego)])
        main()
        extract_output = capsys.readouterr().out
        assert "Hidden message extracted:" in extract_output
        assert secret in extract_output


class TestPackageExports:
    """Tests for package __init__ exports."""

    def test_package_exports(self):
        import fsteg

        assert hasattr(fsteg, "embed")
        assert hasattr(fsteg, "extract")
        assert hasattr(fsteg, "capacity")
        assert hasattr(fsteg, "main")

