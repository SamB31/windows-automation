"""Rainbow ring overlay with status text — Google Gemini-esque animated ring around the screen."""

import colorsys
import ctypes
import threading
import time

import pygame

from config import OVERLAY_RING_SPEED, OVERLAY_RING_WIDTH


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convert HSV (0-1 range) to RGB (0-255 range)."""
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


class RainbowOverlay:
    """Renders an animated rainbow ring border with a status label."""

    def __init__(self):
        self._running = False
        self._thread = None
        self._status = "Starting..."
        self._lock = threading.Lock()

    def set_status(self, text: str):
        """Update the status text shown in the overlay."""
        with self._lock:
            self._status = text

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

        screen = pygame.display.set_mode((w, h), pygame.NOFRAME)
        pygame.display.set_caption("OOBE Overlay")

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
        segments = 360

        # Font for status text
        font = pygame.font.SysFont("consolas", 18, bold=True)

        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break

            screen.fill(colorkey)

            # Re-pin as topmost every frame (OOBE dialogs aggressively steal focus)
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

            # Draw rainbow ring
            t = time.time() * OVERLAY_RING_SPEED
            perimeter = 2 * (w + h)

            for i in range(segments):
                frac = i / segments
                hue = (frac + t) % 1.0
                color = _hsv_to_rgb(hue, 0.9, 1.0)

                pos = frac * perimeter
                if pos < w:
                    rect = (int(pos), 0, max(int(perimeter / segments) + 1, 1), ring_w)
                elif pos < w + h:
                    rect = (w - ring_w, int(pos - w), ring_w, max(int(perimeter / segments) + 1, 1))
                elif pos < 2 * w + h:
                    rect = (int(w - (pos - w - h)), h - ring_w, max(int(perimeter / segments) + 1, 1), ring_w)
                else:
                    rect = (0, int(h - (pos - 2 * w - h)), ring_w, max(int(perimeter / segments) + 1, 1))

                pygame.draw.rect(screen, color, rect)

            # Draw status text with background
            with self._lock:
                status = self._status

            text_surface = font.render(f"  OOBE Automator: {status}  ", True, (255, 255, 255))
            bg_rect = text_surface.get_rect()
            bg_rect.topleft = (ring_w + 4, ring_w + 4)

            # Dark semi-transparent background (use a non-black color since black is colorkey)
            bg = pygame.Surface((bg_rect.width + 8, bg_rect.height + 4))
            bg.fill((1, 1, 1))  # Near-black but not colorkey
            screen.blit(bg, (ring_w + 2, ring_w + 2))
            screen.blit(text_surface, bg_rect)

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
