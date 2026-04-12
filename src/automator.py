"""Windows automation — keyboard and mouse control."""

import ctypes
import logging
import time

import pyautogui

log = logging.getLogger(__name__)

# Safety: disable pyautogui's fail-safe (we're automating OOBE, no corner escape needed)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

# Windows API constants for SendInput
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_SPACE = 0x20

# Key name -> virtual key code mapping for common keys
_VK_MAP = {
    "enter": VK_RETURN, "return": VK_RETURN,
    "tab": VK_TAB, "escape": VK_ESCAPE, "esc": VK_ESCAPE,
    "space": VK_SPACE,
}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT)]


def _send_key_raw(vk_code: int):
    """Send a key press/release using raw Windows SendInput API."""
    extra = ctypes.pointer(ctypes.c_ulong(0))
    # Key down
    inp_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=0, time=0, dwExtraInfo=extra))
    # Key up
    inp_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=extra))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
    time.sleep(0.05)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))


def _focus_behind_overlay():
    """Try to focus the window behind our overlay by clicking the center of the screen."""
    # Get screen size
    w = ctypes.windll.user32.GetSystemMetrics(0)
    h = ctypes.windll.user32.GetSystemMetrics(1)
    # Click center of screen — the overlay is click-through so this focuses the OOBE window
    pyautogui.click(w // 2, h // 2)
    time.sleep(0.1)


def execute_action(action: dict) -> None:
    """Execute an action dict returned by Gemma."""
    action_type = action.get("action", "wait")

    if action_type == "click":
        x = action.get("x", 0)
        y = action.get("y", 0)
        log.info("Clicking at (%d, %d) — %s", x, y, action.get("target", ""))
        pyautogui.click(x, y)

    elif action_type == "type":
        text = action.get("text", "")
        log.info("Typing: %s", text)
        # Click center first to ensure OOBE has focus
        _focus_behind_overlay()
        pyautogui.typewrite(text, interval=0.05)

    elif action_type == "key":
        key = action.get("key", "").lower().strip()
        log.info("Pressing key: %s", key)

        # Click center first to ensure OOBE window has focus, not our overlay
        _focus_behind_overlay()
        time.sleep(0.1)

        # Use raw SendInput for common keys (bypasses any focus issues)
        vk = _VK_MAP.get(key)
        if vk:
            log.info("Sending raw VK code %d for '%s'", vk, key)
            _send_key_raw(vk)
        elif "+" in key:
            keys = [k.strip() for k in key.split("+")]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)

    elif action_type == "wait":
        log.info("Waiting — %s", action.get("reasoning", ""))
        time.sleep(1)

    else:
        log.warning("Unknown action type: %s", action_type)
