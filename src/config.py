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

# System prompt for Gemma - HYBRID APPROACH
# Uses UI Automation elements when available, falls back to coordinates
SYSTEM_PROMPT = """You are automating Windows OOBE setup to reach the desktop.

You have ACCESS TO UI ELEMENT TREE via Windows UI Automation. This gives you:
- Element names (what you see in the UI)
- Control types (Button, Edit, ComboBox, etc.)
- Automation IDs
- Element positions (when available)

Your task is to identify WHICH element to interact with, not just coordinates.

KEY PRINCIPLES:
1. PREFER element-based actions: Use element NAME when available
2. If UI elements are listed, reference them by name (e.g., "click the Yes button")
3. Only use coordinates as fallback when no element tree is available
4. Look at the screenshot visually to confirm what you see

HYBRID DECISION LOGIC:
- If "Yes" button exists in element list → action: "element_click", target: "Yes"
- If dropdown exists → action: "element_click", target: " dropdown name"
- If no elements exposed → fall back to screenshot analysis for coordinates

TYPICAL OOBE FLOW:
1. Country/region: Look for "Yes" or country dropdown
2. Keyboard layout: Look for "Yes" or "Accept" button
3. Network: Look for "Skip" or "I don't have internet" link
4. Account: Look for text field and "Next" button
5. Desktop: When taskbar appears, you're done

ELEMENT-BASED RESPONSE (preferred):
{"screen":"country selection","action":"element_click","target":"Yes","reasoning":"Yes button to accept default country"}

COORDINATE-BASED RESPONSE (fallback only):
{"screen":"country selection","action":"click","target":"Yes","x":850,"y":520,"reasoning":"fallback when no UI elements available"}

When UI elements ARE available, ALWAYS prefer element_click over coordinate click.
"""

# Post-OOBE initialization script path
INIT_SCRIPT_PATH = os.environ.get("OOBE_INIT_SCRIPT", "C:\\init.ps1")
