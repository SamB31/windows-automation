"""OOBE Automator — main entry point.

Captures screenshots, analyzes them with Gemma 3 4B, and automates
Windows OOBE until the desktop is reached.
"""

import logging
import subprocess
import sys
import time

from config import CYCLE_DELAY, INIT_SCRIPT_PATH
from gemma import analyze_screen, create_client
from overlay import RainbowOverlay
from screenshot import capture_screen_base64
from automator import execute_action

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
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

    # Connect to ollama
    client = create_client()
    log.info("Connected to ollama endpoint")

    consecutive_failures = 0
    max_failures = 10

    try:
        while True:
            # Capture screenshot
            screenshot_b64, screen_size = capture_screen_base64()
            log.info("Captured screenshot (%dx%d)", *screen_size)

            # Analyze with Gemma
            action = analyze_screen(client, screenshot_b64, screen_size)

            # Check if we've reached the desktop
            if action.get("at_desktop"):
                log.info("Desktop reached! Running initialization script...")
                overlay.stop()
                run_init_script()
                log.info("=== OOBE Automation complete ===")
                break

            # Execute the action
            if action.get("action") == "wait" and "error" in action.get("reasoning", "").lower():
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    log.error("Too many consecutive failures (%d), exiting", max_failures)
                    break
            else:
                consecutive_failures = 0

            execute_action(action)

            # Wait before next cycle
            time.sleep(CYCLE_DELAY)

    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        overlay.stop()
        log.info("Overlay stopped, exiting")


if __name__ == "__main__":
    main()
