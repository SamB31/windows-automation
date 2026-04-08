"""Windows automation — keyboard and mouse control."""

import logging
import time

import pyautogui

log = logging.getLogger(__name__)

# Safety: disable pyautogui's fail-safe (we're automating OOBE, no corner escape needed)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3


def execute_action(action: dict) -> None:
    """Execute an action dict returned by Gemma.

    Supported actions:
        click  — click at (x, y)
        type   — type text string
        key    — press a key or key combo
        wait   — do nothing this cycle
    """
    action_type = action.get("action", "wait")

    if action_type == "click":
        x = action.get("x", 0)
        y = action.get("y", 0)
        log.info("Clicking at (%d, %d) — %s", x, y, action.get("target", ""))
        pyautogui.click(x, y)

    elif action_type == "type":
        text = action.get("text", "")
        log.info("Typing: %s", text)
        pyautogui.typewrite(text, interval=0.05)

    elif action_type == "key":
        key = action.get("key", "")
        log.info("Pressing key: %s", key)
        if "+" in key:
            keys = [k.strip() for k in key.split("+")]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)

    elif action_type == "wait":
        log.info("Waiting — %s", action.get("reasoning", ""))
        time.sleep(1)

    else:
        log.warning("Unknown action type: %s", action_type)
