"""Configuration for OOBE Automator."""

import json
import os
import sys
import tempfile


def _resource_path(relative: str) -> str:
    """Get path to bundled resource, works for PyInstaller --onefile."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", relative)


def _reassemble_model(name: str) -> str:
    """Reassemble a model from chunks if needed (PyInstaller 4GB workaround).

    If the file exists as-is, return it directly.
    If a manifest.json exists with chunk info, reassemble to a temp file.
    """
    direct = _resource_path(name)
    if os.path.exists(direct):
        return direct

    manifest_path = _resource_path("manifest.json")
    if not os.path.exists(manifest_path):
        return direct  # will fail later with a clear error

    with open(manifest_path) as f:
        manifest = json.load(f)

    if name not in manifest:
        return direct

    chunks = manifest[name]
    if len(chunks) == 1:
        return _resource_path(chunks[0])

    # Reassemble chunks into a temp file
    temp_dir = os.path.join(tempfile.gettempdir(), "oobe-automator")
    os.makedirs(temp_dir, exist_ok=True)
    output_path = os.path.join(temp_dir, name)

    if os.path.exists(output_path):
        # Already reassembled from a previous run
        expected_size = sum(os.path.getsize(_resource_path(c)) for c in chunks)
        if os.path.getsize(output_path) == expected_size:
            return output_path

    print(f"Reassembling {name} from {len(chunks)} chunks...")
    with open(output_path, "wb") as out:
        for chunk_name in chunks:
            chunk_path = _resource_path(chunk_name)
            with open(chunk_path, "rb") as inp:
                while True:
                    data = inp.read(64 * 1024 * 1024)  # 64MB buffer
                    if not data:
                        break
                    out.write(data)
    print(f"Reassembled {name} ({os.path.getsize(output_path) / (1024**3):.2f}GB)")
    return output_path


# Bundled model paths (GGUF files included in the exe)
MODEL_PATH = os.environ.get("OOBE_MODEL_PATH") or _reassemble_model("gemma-4-E4B-it.gguf")
MMPROJ_PATH = os.environ.get("OOBE_MMPROJ_PATH") or _reassemble_model("gemma-4-E4B-it-mmproj.gguf")

# Context size for the model
MODEL_CTX_SIZE = 4096

# Number of GPU layers to offload (-1 = all, 0 = CPU only)
MODEL_GPU_LAYERS = int(os.environ.get("OOBE_GPU_LAYERS", "0"))

# How long to wait between screenshot-analyze-act cycles (seconds)
CYCLE_DELAY = float(os.environ.get("OOBE_CYCLE_DELAY", "3.0"))

# Screenshot quality (1-100 for JPEG)
SCREENSHOT_QUALITY = 85

# Overlay settings
OVERLAY_RING_WIDTH = 8
OVERLAY_RING_SPEED = 2.0  # rotations per second
OVERLAY_OPACITY = 200  # 0-255

# System prompt for Gemma
SYSTEM_PROMPT = """You are automating Windows OOBE setup to reach the desktop.

PREFER MOUSE CLICKS — only use keyboard when you must type text:
- Use "click" action with x,y coordinates to click buttons directly
- Use "type" action ONLY when you see a text input field that needs typing
- Use "key" action only for "tab" to navigate between elements, then click

SCREEN-BY-SCREEN GUIDE:
- Country/region screen: click on the "Yes" button
- Keyboard layout: click "Yes" or "Accept"
- Second keyboard layout: click "Skip" or "Next"
- Network/Wi-Fi: click "I don't have internet" or similar, then click "Continue"
- Name field: click the name input field, type "Admin", then click "Next"
- Password field: click "Next" (leave blank)
- Security questions: type any answers, click "Next"
- Privacy settings: click "Accept" or "Next"
- If you see the desktop (taskbar, start menu): set "at_desktop": true

IMPORTANT: Always provide actual x,y pixel coordinates for click actions. The screen resolution is passed to you.

Respond with ONLY a JSON object:
{"screen":"description","action":"click|type|key|wait","target":"what","x":0,"y":0,"text":"","key":"","reasoning":"why","at_desktop":false}
"""

# Post-OOBE initialization script path
INIT_SCRIPT_PATH = os.environ.get("OOBE_INIT_SCRIPT", "C:\\init.ps1")
