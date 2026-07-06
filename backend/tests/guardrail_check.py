from __future__ import annotations

import io
import math
import sys
import struct
import wave
from pathlib import Path

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.url_loader import _extract_text
from utils.file_handler import validate_file
from utils.security import validate_public_url


class FakeUpload:
    def __init__(self, filename: str):
        self.filename = filename


def make_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    sample_rate = 8000
    duration_seconds = 1
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = []
        for index in range(sample_rate * duration_seconds):
            sample = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.append(struct.pack("<h", sample))
        wav_file.writeframes(b"".join(frames))
    return buffer.getvalue()


def expect_ok(label: str, fn):
    fn()
    print(f"PASS {label}")


def expect_http_error(label: str, fn, status_code: int = 400):
    try:
        fn()
    except HTTPException as exc:
        assert exc.status_code == status_code, f"{label}: expected {status_code}, got {exc.status_code}"
        print(f"PASS {label}: {exc.detail}")
        return
    raise AssertionError(f"{label}: expected HTTPException")


def main():
    valid_wav = make_wav_bytes()

    expect_ok(
        "valid wav accepted",
        lambda: validate_file(FakeUpload("sample.wav"), valid_wav),
    )
    expect_http_error(
        "corrupted wav rejected",
        lambda: validate_file(FakeUpload("corrupted.wav"), b"not really an audio file"),
    )
    expect_http_error(
        "empty upload rejected",
        lambda: validate_file(FakeUpload("empty.wav"), b""),
    )
    expect_http_error(
        "unsupported extension rejected",
        lambda: validate_file(FakeUpload("payload.exe"), valid_wav),
    )
    expect_http_error(
        "fake extension rejected",
        lambda: validate_file(FakeUpload("fake.pdf"), valid_wav),
    )

    expect_http_error("file scheme url blocked", lambda: validate_public_url("file:///etc/passwd"))
    expect_http_error("localhost url blocked", lambda: validate_public_url("http://localhost:8000"))
    expect_http_error("private ip url blocked", lambda: validate_public_url("http://127.0.0.1:8000"))
    expect_http_error("metadata service url blocked", lambda: validate_public_url("http://169.254.169.254/latest/meta-data"))
    expect_http_error("unresolvable url blocked", lambda: validate_public_url("https://ragverse-invalid-domain.invalid"))
    expect_http_error(
        "thin html rejected",
        lambda: _extract_text("<html><title>Short</title><body><p>too short</p></body></html>"),
    )

    print("All guardrail checks passed.")


if __name__ == "__main__":
    main()
