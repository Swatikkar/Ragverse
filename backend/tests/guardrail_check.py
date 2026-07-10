from __future__ import annotations

import io
import math
import sys
import struct
import wave
import zipfile
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


def make_zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for name, value in entries.items():
            zip_file.writestr(name, value)
    return buffer.getvalue()


def make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def make_csv_bytes() -> bytes:
    return b"name,score\nRagverse,100\n"


def make_mp3_bytes() -> bytes:
    return b"ID3\x04\x00\x00\x00\x00\x00\x15TIT2\x00\x00\x00\x03\x00\x00Hi!"


def make_m4a_bytes() -> bytes:
    return b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00M4A mp42"


def make_ogg_bytes() -> bytes:
    return b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00"


def make_webm_bytes() -> bytes:
    return b"\x1A\x45\xDF\xA3\x00\x00\x00\x00\x42\x82\x84webm"


def make_mp4_bytes() -> bytes:
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"


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
    valid_docx = make_zip_bytes({
        "[Content_Types].xml": "<Types></Types>",
        "word/document.xml": "<w:document></w:document>",
    })
    valid_xlsx = make_zip_bytes({
        "[Content_Types].xml": "<Types></Types>",
        "xl/workbook.xml": "<workbook></workbook>",
    })
    valid_pptx = make_zip_bytes({
        "[Content_Types].xml": "<Types></Types>",
        "ppt/presentation.xml": "<p:presentation></p:presentation>",
    })

    expect_ok("pdf validation accepted", lambda: validate_file(FakeUpload("sample.pdf"), make_pdf_bytes()))
    expect_ok("csv validation accepted", lambda: validate_file(FakeUpload("sample.csv"), make_csv_bytes()))
    expect_ok("docx validation accepted", lambda: validate_file(FakeUpload("sample.docx"), valid_docx))
    expect_ok("xlsx validation accepted", lambda: validate_file(FakeUpload("sample.xlsx"), valid_xlsx))
    expect_ok("pptx validation accepted", lambda: validate_file(FakeUpload("sample.pptx"), valid_pptx))
    expect_ok(
        "wav validation accepted",
        lambda: validate_file(FakeUpload("sample.wav"), valid_wav),
    )
    expect_ok("mp3 validation accepted", lambda: validate_file(FakeUpload("sample.mp3"), make_mp3_bytes()))
    expect_ok("m4a validation accepted", lambda: validate_file(FakeUpload("sample.m4a"), make_m4a_bytes()))
    expect_ok("ogg validation accepted", lambda: validate_file(FakeUpload("sample.ogg"), make_ogg_bytes()))
    expect_ok("webm validation accepted", lambda: validate_file(FakeUpload("sample.webm"), make_webm_bytes()))
    expect_ok("mp4 validation accepted", lambda: validate_file(FakeUpload("sample.mp4"), make_mp4_bytes()))
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
