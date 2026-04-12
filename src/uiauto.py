"""UI Automation module for Windows OOBE.

Uses pywinauto to access the UI element tree via Windows UI Automation (UIA).
This allows element-based clicks rather than coordinate-based clicks.
"""

import ctypes
import logging
import time
from typing import Optional

log = logging.getLogger(__name__)

# Lazy import pywinauto - it's only available on Windows
_pywinauto = None

def _get_pywinauto():
    global _pywinauto
    if _pywinauto is None:
        import importlib
        try:
            _pywinauto = importlib.import_module("pywinauto")
        except ImportError:
            log.warning("pywinauto not available - UI automation disabled")
            return None
    return _pywinauto


class UIElement:
    """Represents a UI element with its automation properties."""
    
    def __init__(
        self,
        name: str,
        control_type: str,
        auto_id: Optional[str] = None,
        rect=None,
        is_enabled: bool = True,
        is_visible: bool = True,
    ):
        self.name = name
        self.control_type = control_type
        self.auto_id = auto_id
        self.rect = rect  # (left, top, right, bottom)
        self.is_enabled = is_enabled
        self.is_visible = is_visible
    
    @property
    def center_x(self) -> int:
        if self.rect:
            return (self.rect[0] + self.rect[2]) // 2
        return 0
    
    @property
    def center_y(self) -> int:
        if self.rect:
            return (self.rect[1] + self.rect[3]) // 2
        return 0
    
    def matches_name(self, text: str) -> bool:
        """Check if element name contains the given text (case-insensitive)."""
        if not self.name:
            return False
        return text.lower() in self.name.lower()
    
    def __repr__(self):
        return f"UIElement(name='{self.name}', type={self.control_type}, auto_id={self.auto_id})"


def _get_backend_name() -> str:
    """Get the best available pywinauto backend name."""
    pw = _get_pywinauto()
    if pw is None:
        return "uia"
    try:
        pw.Desktop(backend="uia")
        return "uia"
    except Exception:
        return "win32"


def get_all_elements() -> list[UIElement]:
    """Get all UI elements from the current foreground window.
    
    Returns a list of UIElement objects with names, types, and positions.
    """
    pw = _get_pywinauto()
    if pw is None:
        return []
    
    try:
        backend = _get_backend_name()
        desktop = pw.Desktop(backend=backend)
        
        # Get all top-level windows
        windows = desktop.windows()
        
        elements = []
        for win in windows:
            try:
                # Skip our own overlay window
                title = ""
                try:
                    title = win.window_text()
                except Exception:
                    pass
                
                if "oobe-automator" in title.lower() or "overlay" in title.lower():
                    continue
                
                # Get all descendants
                _collect_elements(win, elements, depth=0, max_depth=5)
            except Exception as e:
                log.debug("Error processing window: %s", e)
                continue
        
        log.info("Found %d UI elements", len(elements))
        return elements
        
    except Exception as e:
        log.warning("Failed to get UI elements: %s", e)
        return []


def _collect_elements(parent, elements: list, depth: int, max_depth: int):
    """Recursively collect UI elements from a parent."""
    if depth > max_depth:
        return
    
    try:
        children = parent.children()
        for child in children:
            try:
                # Get element properties
                name = ""
                ctrl_type = ""
                auto_id = ""
                is_enabled = True
                is_visible = True
                rect = None
                
                try:
                    name = child.window_text() or ""
                except Exception:
                    pass
                
                try:
                    ctrl_type = child.control_type() if hasattr(child, 'control_type') else ""
                except Exception:
                    try:
                        ctrl_type = child.friendly_class_name() or ""
                    except Exception:
                        pass
                
                try:
                    auto_id = child.automation_id() if hasattr(child, 'automation_id') else ""
                except Exception:
                    pass
                
                try:
                    is_enabled = child.is_enabled()
                except Exception:
                    pass
                
                try:
                    is_visible = child.is_visible()
                except Exception:
                    pass
                
                try:
                    rect = child.rectangle()
                    if rect:
                        rect = (rect.left, rect.top, rect.right, rect.bottom)
                except Exception:
                    pass
                
                # Only add elements with meaningful names
                if name and ctrl_type:
                    elements.append(UIElement(
                        name=name,
                        control_type=ctrl_type,
                        auto_id=auto_id,
                        rect=rect,
                        is_enabled=is_enabled,
                        is_visible=is_visible,
                    ))
                
                # Recurse into children
                _collect_elements(child, elements, depth + 1, max_depth)
                
            except Exception as e:
                log.debug("Error processing child: %s", e)
                continue
    except Exception as e:
        log.debug("Error getting children: %s", e)


def find_element_by_name(elements: list[UIElement], name: str) -> Optional[UIElement]:
    """Find an element by name (case-insensitive partial match)."""
    name_lower = name.lower()
    for elem in elements:
        if elem.name and name_lower in elem.name.lower():
            return elem
    return None


def find_elements_by_type(elements: list[UIElement], ctrl_type: str) -> list[UIElement]:
    """Find all elements of a specific control type."""
    ctrl_type_lower = ctrl_type.lower()
    return [e for e in elements if e.control_type and ctrl_type_lower in e.control_type.lower()]


def find_button(elements: list[UIElement], text: str) -> Optional[UIElement]:
    """Find a button by text (case-insensitive partial match)."""
    # First try to find by name
    btn = find_element_by_name(elements, text)
    if btn:
        return btn
    
    # Then try to find any button with that text
    buttons = find_elements_by_type(elements, "button")
    for b in buttons:
        if b.matches_name(text):
            return b
    
    return None


def format_elements_for_prompt(elements: list[UIElement]) -> str:
    """Format UI elements as text for the AI prompt."""
    if not elements:
        return "No UI elements detected via automation."
    
    lines = ["Available UI Elements:"]
    for i, elem in enumerate(elements):
        if not elem.is_visible or not elem.is_enabled:
            continue
        
        # Format: [1] Button: "Yes" (auto_id=1234) at (100, 200)
        location = ""
        if elem.rect:
            location = f"center=({elem.center_x},{elem.center_y})"
        
        auto_id_str = f", auto_id={elem.auto_id}" if elem.auto_id else ""
        
        lines.append(f"  [{i}] {elem.control_type}: '{elem.name}'{auto_id_str} {location}")
    
    return "\n".join(lines)


def click_element(elem: UIElement) -> bool:
    """Click a UI element at its center coordinates.

    Uses pyautogui to click at the element's known center position.
    This is faster and more reliable than re-searching the UI tree.
    Returns True if successful, False otherwise.
    """
    if not elem.rect:
        log.warning("Element has no rect, cannot click: %s", elem)
        return False

    try:
        import pyautogui
        x, y = elem.center_x, elem.center_y
        log.info("Clicking element '%s' at (%d, %d)", elem.name, x, y)
        pyautogui.click(x, y)
        return True
    except Exception as e:
        log.error("Failed to click element: %s", e)
        return False


def get_clickable_elements(elements: list[UIElement]) -> list[UIElement]:
    """Filter to only clickable elements (buttons, links, etc.)."""
    clickable_types = ["button", "link", "hyperlink", "tab", "menuitem", "listitem"]
    return [
        e for e in elements
        if e.is_visible and e.is_enabled and
        e.control_type and any(t in e.control_type.lower() for t in clickable_types)
    ]