"""Screen capture module using mss."""

import base64
import io

import mss
from PIL import Image


def capture_screen() -> Image.Image:
    """Capture the primary monitor and return as PIL Image."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def capture_screen_base64() -> tuple[str, tuple[int, int]]:
    """Capture screen and return as base64-encoded JPEG + dimensions."""
    img = capture_screen()
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return b64, img.size
