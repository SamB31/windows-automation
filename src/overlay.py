"""Rainbow ring overlay — Google Gemini-esque animated ring around the screen."""

import math
import threading
import time

import pygame

from config import OVERLAY_OPACITY, OVERLAY_RING_SPEED, OVERLAY_RING_WIDTH


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convert HSV (0-1 range) to RGB (0-255 range)."""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


class RainbowOverlay:
    """Renders an animated rainbow ring border around the entire screen."""

    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        """Start the overlay in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the overlay."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        """Main overlay loop."""
        pygame.init()
        info = pygame.display.Info()
        w, h = info.current_w, info.current_h

        # Create a borderless, topmost, transparent window
        screen = pygame.display.set_mode((w, h), pygame.NOFRAME)
        pygame.display.set_caption("OOBE Overlay")

        # Make the window transparent and topmost via Windows API
        import ctypes
        from ctypes import wintypes

        hwnd = pygame.display.get_wm_info()["window"]
        user32 = ctypes.windll.user32
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        WS_EX_TRANSPARENT = 0x20
        WS_EX_TOPMOST = 0x8
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x2
        SWP_NOSIZE = 0x1
        LWA_COLORKEY = 0x1

        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        user32.SetLayeredWindowAttributes(hwnd, 0x00000000, 0, LWA_COLORKEY)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

        clock = pygame.time.Clock()
        colorkey = (0, 0, 0)  # Black is transparent

        ring_w = OVERLAY_RING_WIDTH
        segments = 360  # one segment per degree

        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break

            screen.fill(colorkey)

            t = time.time() * OVERLAY_RING_SPEED
            perimeter = 2 * (w + h)

            for i in range(segments):
                frac = i / segments
                hue = (frac + t) % 1.0
                color = _hsv_to_rgb(hue, 0.9, 1.0)

                # Map fraction around the screen perimeter
                pos = frac * perimeter
                if pos < w:  # Top edge
                    x, y = pos, 0
                    rect = (int(x), 0, max(int(perimeter / segments) + 1, 1), ring_w)
                elif pos < w + h:  # Right edge
                    x, y = w - ring_w, pos - w
                    rect = (w - ring_w, int(y), ring_w, max(int(perimeter / segments) + 1, 1))
                elif pos < 2 * w + h:  # Bottom edge
                    x, y = w - (pos - w - h), h - ring_w
                    rect = (int(x), h - ring_w, max(int(perimeter / segments) + 1, 1), ring_w)
                else:  # Left edge
                    x, y = 0, h - (pos - 2 * w - h)
                    rect = (0, int(y), ring_w, max(int(perimeter / segments) + 1, 1))

                pygame.draw.rect(screen, color, rect)

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
