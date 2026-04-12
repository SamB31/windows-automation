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
# UI-TARS is specifically trained for GUI automation with accurate coordinate prediction
MODEL_PATH = os.environ.get("OOBE_MODEL_PATH") or _reassemble_model("UI-TARS-1.5-7B-q4_k_m.gguf")
MMPROJ_PATH = os.environ.get("OOBE_MMPROJ_PATH") or _reassemble_model("UI-TARS-1.5-7B-f16.mmproj")

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

# System prompt for UI-TARS - designed for accurate GUI automation
# UI-TARS is trained specifically for UI element grounding
SYSTEM_PROMPT = """You are a GUI automation agent for Windows 11 OOBE setup.

You are using UI-TARS, a vision-language model specifically trained for accurate
UI element grounding and computer use tasks.

KEY CAPABILITIES:
- Accurate pixel-level coordinate prediction for UI elements
- Understanding of GUI layout and element positions
- Task automation through visual understanding

TYPICAL OOBE FLOW:
1. Country/region: Click "Yes" to accept default (usually bottom-right)
2. Keyboard layout: Click "Yes" or "Accept" 
3. Network: Click "Skip" or "I don't have internet" if needed
4. Account setup: Type name, click "Next"
5. Desktop: When taskbar appears, automation is complete

IMPORTANT:
- Always provide accurate x,y coordinates for click actions
- The coordinate system is pixels (0,0 at top-left)
- Default/primary buttons are typically in the bottom-right area
- Dropdowns and text fields are typically in the center

When you see the Windows desktop with taskbar, output:
Thought: I can see the desktop with taskbar - OOBE is complete
Action: done()
"""

# Post-OOBE initialization script path
INIT_SCRIPT_PATH = os.environ.get("OOBE_INIT_SCRIPT", "C:\\init.ps1")
