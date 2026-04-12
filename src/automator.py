"""Windows automation — keyboard and mouse control.

This module supports both:
1. Element-based clicks (preferred) - uses UI Automation via pywinauto
2. Coordinate-based clicks (fallback) - uses pyautogui with x,y coordinates
"""

import ctypes
import logging
import time
from typing import Optional

import pyautogui

from uiauto import find_button, click_element, UIElement

log = logging.getLogger(__name__)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_SPACE = 0x20

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
    extra = ctypes.pointer(ctypes.c_ulong(0))
    inp_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=0, time=0, dwExtraInfo=extra))
    inp_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=extra))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
    time.sleep(0.05)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))


def _bring_oobe_to_foreground():
    """Find and bring the OOBE window to foreground."""
    user32 = ctypes.windll.user32
    
    overlay_hwnd = None
    oobe_hwnd = None
    
    def enum_callback(hwnd, _):
        nonlocal overlay_hwnd, oobe_hwnd
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value
        
        if "OOBE Overlay" in title or "oobe-automator" in title.lower():
            overlay_hwnd = hwnd
        elif hwnd != overlay_hwnd:
            oobe_hwnd = hwnd
        return True
    
    enumfunc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_long, ctypes.c_long)(enum_callback)
    user32.EnumWindows(enumfunc, 0)
    
    if oobe_hwnd:
        user32.SetForegroundWindow(oobe_hwnd)
        time.sleep(0.1)


def execute_action(action: dict, ui_elements: list[UIElement] = None) -> None:
    """Execute an action dict returned by Gemma.
    
    Supports both element-based clicks (via UI Automation) and 
    coordinate-based clicks (via pyautogui) as fallback.
    """
    action_type = action.get("action", "wait")
    target = action.get("target", "")

    if action_type == "element_click":
        # HYBRID: Element-based click using UI Automation
        target_name = target
        log.info("Element-click on '%s'", target_name)
        
        if ui_elements:
            elem = find_button(ui_elements, target_name)
            if elem:
                log.info("Found element: %s at center (%d, %d)", elem.name, elem.center_x, elem.center_y)
                _bring_oobe_to_foreground()
                success = click_element(elem)
                if success:
                    log.info("Successfully clicked element via UI Automation")
                    return
                else:
                    log.warning("UI Automation click failed, falling back to coordinates")
            else:
                log.info("Element '%s' not found in UI tree, falling back to screenshot analysis", target_name)
                log.info("Available elements: %s", [e.name for e in ui_elements[:10]])
        
        # Fallback to coordinate-based click
        x = action.get("x", 0)
        y = action.get("y", 0)
        log.info("Fallback: clicking at (%d, %d)", x, y)
        _bring_oobe_to_foreground()
        pyautogui.click(x, y)

    elif action_type == "click":
        # Coordinate-based click (original behavior)
        x = action.get("x", 0)
        y = action.get("y", 0)
        log.info("Clicking at (%d, %d) — %s", x, y, target)
        _bring_oobe_to_foreground()
        pyautogui.click(x, y)

    elif action_type == "type":
        text = action.get("text", "")
        log.info("Typing: %s", text)
        _bring_oobe_to_foreground()
        pyautogui.typewrite(text, interval=0.05)

    elif action_type == "key":
        key = action.get("key", "").lower().strip()
        log.info("Pressing key: %s", key)

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
