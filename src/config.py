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

Your task is to look at the screenshot and identify EXACT x,y pixel click coordinates.

KEY PRINCIPLES:
1. Look at the screenshot image carefully - you can see the exact positions of UI elements
2. Report the CENTER of any button you want to click (not the edge)
3. Buttons in Windows OOBE are typically 100-200px wide and 30-50px tall
4. Default/primary buttons (like "Yes", "Next", "Accept") are usually on the RIGHT or BOTTOM

TYPICAL PATTERNS IN WINDOWS OOBE:
- "Yes" / "Accept" / "Next" buttons: Usually on the RIGHT side of dialogs, or BOTTOM-right
- Dropdowns for country: Usually CENTER-LEFT of screen
- Text input fields: Usually CENTER of screen with label above
- Checkboxes: Small square, usually LEFT side with text to the right

STEP-BY-STEP:
1. Country/region screen: Find "Yes" button (blue/purple, right or bottom), click its center
2. Keyboard layout: Click "Yes" or "Accept" (bottom area)
3. Network: Click "I don't have internet" text link (usually bottom-left), then "Continue"
4. Name setup: Click text field, type "Admin", then click "Next" (bottom-right)
5. Password: Click "Next" (leave blank)
6. Privacy: Click "Accept" or "Next"
7. Desktop: When you see taskbar/icons, set "at_desktop": true

Respond with ONLY a JSON object with exact coordinates:
{"screen":"what you see","action":"click","target":"button name","x":CENTER_X,"y":CENTER_Y,"reasoning":"why this coordinate"}
"""

# Post-OOBE initialization script path
INIT_SCRIPT_PATH = os.environ.get("OOBE_INIT_SCRIPT", "C:\\init.ps1")
