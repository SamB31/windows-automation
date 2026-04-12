"""OOBE Automator — main entry point.

Captures screenshots, analyzes them with Gemma 4 E4B, and automates
Windows OOBE until the desktop is reached.

HYBRID APPROACH: Uses UI Automation (pywinauto) when available to get
element tree, combined with vision model analysis for decision-making.
Element-based clicks are preferred over coordinate-based clicks.
"""

import logging
import os
import subprocess
import sys
import tempfile
import time

from config import CYCLE_DELAY, INIT_SCRIPT_PATH
from gemma import analyze_screen, load_model
from overlay import RainbowOverlay
from screenshot import capture_screen_base64
from automator import execute_action
from uiauto import get_all_elements

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(tempfile.gettempdir(), "oobe-automator.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger("oobe-automator")


def run_init_script():
    """Run the post-OOBE initialization script."""
    log.info("Running initialization script: %s", INIT_SCRIPT_PATH)
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", INIT_SCRIPT_PATH],
            capture_output=True,
            text=True,
            timeout=300,
        )
        log.info("Init script stdout: %s", result.stdout)
        if result.returncode != 0:
            log.error("Init script failed (exit %d): %s", result.returncode, result.stderr)
    except FileNotFoundError:
        log.warning("Init script not found at %s — skipping", INIT_SCRIPT_PATH)
    except subprocess.TimeoutExpired:
        log.error("Init script timed out after 300s")


def main():
    log.info("=== OOBE Automator starting ===")

    # Start rainbow overlay
    overlay = RainbowOverlay()
    overlay.start()
    log.info("Rainbow overlay started")

    # Load bundled Gemma 4 E4B model
    overlay.set_status("Loading Gemma 4 E4B model...")
    log.info("Loading Gemma 4 E4B model (this may take a moment)...")
    llm = load_model()
    overlay.set_status("Model loaded, ready")
    log.info("Model loaded and ready")

    consecutive_failures = 0
    max_failures = 10
    cycle = 0

    try:
        while True:
            cycle += 1

            # Capture screenshot
            overlay.set_status(f"[{cycle}] Taking screenshot...")
            screenshot_b64, screen_size = capture_screen_base64()
            log.info("Captured screenshot (%dx%d)", *screen_size)

            # HYBRID: Get UI elements via UI Automation
            ui_elements = get_all_elements()
            log.info("UI elements found: %d", len(ui_elements))

            # Analyze with Gemma (pass UI elements for element-based decisions)
            overlay.set_status(f"[{cycle}] Analyzing screen with Gemma...")
            action = analyze_screen(llm, screenshot_b64, screen_size, ui_elements)

            # Check if we've reached the desktop
            if action.get("at_desktop"):
                overlay.set_status("Desktop reached! Running init script...")
                log.info("Desktop reached! Running initialization script...")
                overlay.stop()
                run_init_script()
                log.info("=== OOBE Automation complete ===")
                break

            # Execute the action
            action_type = action.get("action", "wait")
            screen_desc = action.get("screen", "unknown")

            if action_type == "element_click":
                overlay.set_status(f"[{cycle}] Element-click: {action.get('target', '')} — {screen_desc}")
            elif action_type == "click":
                overlay.set_status(f"[{cycle}] Clicking ({action.get('x')}, {action.get('y')}) — {screen_desc}")
            elif action_type == "type":
                overlay.set_status(f"[{cycle}] Typing: {action.get('text', '')}")
            elif action_type == "key":
                overlay.set_status(f"[{cycle}] Pressing: {action.get('key', '')}")
            else:
                overlay.set_status(f"[{cycle}] Waiting — {action.get('reasoning', '')[:60]}")

            if action_type == "wait" and "error" in action.get("reasoning", "").lower():
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    log.error("Too many consecutive failures (%d), exiting", max_failures)
                    break
            else:
                consecutive_failures = 0

            # Get UI elements from action (set by analyzer)
            action_ui_elements = action.get("_ui_elements", None)
            execute_action(action, action_ui_elements)

            # Wait before next cycle
            time.sleep(CYCLE_DELAY)

    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        overlay.stop()
        log.info("Overlay stopped, exiting")


if __name__ == "__main__":
    main()
