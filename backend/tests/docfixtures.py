"""Synthetic documents for tests. Fake data only; the numbers below are not real IDs."""

from __future__ import annotations

import io

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

VALID_AADHAAR = "2345 6789 0124"  # Verhoeff-valid test number


def render(lines: list[str], size: tuple[int, int] = (1700, 1200), font_px: int = 34) -> Image.Image:
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=font_px)
    y = 60
    for line in lines:
        draw.text((70, y), line, fill="black", font=font)
        y += font_px + 22
    return img


def png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def jpeg_blurred(img: Image.Image, k: int = 61) -> bytes:
    arr = cv2.GaussianBlur(np.array(img), (k, k), 0)
    ok, out = cv2.imencode(".jpg", arr)
    assert ok
    return out.tobytes()


def pdf(lines: list[str]) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    y = 80
    for line in lines:
        page.insert_text((60, y), line, fontsize=14)
        y += 26
    return doc.tobytes()


INCOME = [
    "GOVERNMENT OF NCT OF DELHI",
    "Office of the SDM (Revenue Department)",
    "INCOME CERTIFICATE",
    "Name of the Applicant: Asha Verma",
    "Annual Income: Rs. 240000",
    "Date of Issue: 12/09/2026",
]
