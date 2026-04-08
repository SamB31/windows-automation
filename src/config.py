"""Configuration for OOBE Automator."""

import os

# Ollama endpoint — override with OLLAMA_HOST env var
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Model to use for vision analysis
MODEL_NAME = os.environ.get("OOBE_MODEL", "gemma3:4b")

# How long to wait between screenshot-analyze-act cycles (seconds)
CYCLE_DELAY = float(os.environ.get("OOBE_CYCLE_DELAY", "3.0"))

# Screenshot quality (1-100 for JPEG)
SCREENSHOT_QUALITY = 85

# Overlay settings
OVERLAY_RING_WIDTH = 8
OVERLAY_RING_SPEED = 2.0  # rotations per second
OVERLAY_OPACITY = 200  # 0-255

# System prompt for Gemma
SYSTEM_PROMPT = """You are an AI assistant automating the Windows Out-of-Box Experience (OOBE).
Your goal is to navigate through all OOBE screens and reach the Windows desktop.

When you see a screenshot, analyze what OOBE screen is shown and respond with the EXACT action to take.

Respond in this JSON format:
{
    "screen": "brief description of current screen",
    "action": "click" | "type" | "key" | "wait",
    "target": "description of where to click (for click actions)",
    "x": pixel_x (for click actions),
    "y": pixel_y (for click actions),
    "text": "text to type (for type actions)",
    "key": "key name (for key actions, e.g. 'enter', 'tab', 'escape')",
    "reasoning": "why this action gets us closer to the desktop",
    "at_desktop": false
}

Guidelines:
- Skip Microsoft account sign-in: use offline account options
- Accept default settings where possible to move quickly
- For region/keyboard selection: use United States / US keyboard
- Set a simple password or no password for the local account
- Username: "Admin"
- If you see the desktop (taskbar, start menu, icons), set "at_desktop": true
- Be precise with click coordinates based on the screenshot dimensions
"""

# Post-OOBE initialization script path
INIT_SCRIPT_PATH = os.environ.get("OOBE_INIT_SCRIPT", "C:\\init.ps1")
