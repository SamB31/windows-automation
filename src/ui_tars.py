"""UI-TARS vision — runs locally via llama-cpp-python with bundled GGUF weights.

UI-TARS is specifically trained for GUI agent tasks with accurate coordinate prediction.
Built on Qwen2-VL architecture — uses Qwen25VLChatHandler and ChatML format.
Coordinates are normalized 0-1000 and converted to pixel values.
"""

import json
import logging
import re

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Qwen25VLChatHandler

from config import (
    MODEL_PATH,
    MMPROJ_PATH,
    MODEL_CTX_SIZE,
    MODEL_GPU_LAYERS,
    SYSTEM_PROMPT,
)

log = logging.getLogger(__name__)


def load_model() -> Llama:
    """Load the bundled UI-TARS model with vision support."""
    log.info("Loading vision projector from %s", MMPROJ_PATH)
    chat_handler = Qwen25VLChatHandler(clip_model_path=MMPROJ_PATH, verbose=False)

    log.info("Loading model from %s", MODEL_PATH)
    llm = Llama(
        model_path=MODEL_PATH,
        chat_handler=chat_handler,
        n_ctx=MODEL_CTX_SIZE,
        n_gpu_layers=MODEL_GPU_LAYERS,
        n_ubatch=2048,
        verbose=False,
    )
    log.info("Model loaded successfully")
    return llm


def _normalize_to_pixels(raw_x: int, raw_y: int, screen_w: int, screen_h: int) -> tuple[int, int]:
    """Convert UI-TARS normalized coords (0-1000) to pixel coords."""
    pixel_x = int(raw_x * screen_w / 1000)
    pixel_y = int(raw_y * screen_h / 1000)
    return pixel_x, pixel_y


def parse_ui_tars_response(text: str, screen_size: tuple[int, int]) -> dict:
    """Parse UI-TARS response into action dict.

    UI-TARS outputs actions like:
        Thought: reasoning text
        Action: click(start_box='(177,549)')

    Coordinates are normalized 0-1000 and converted to pixels.
    """
    reasoning = ""
    screen_w, screen_h = screen_size

    # Extract thought/reasoning
    thought_match = re.search(r"Thought:\s*(.+?)(?:\nAction:|$)", text, re.IGNORECASE | re.DOTALL)
    if thought_match:
        reasoning = thought_match.group(1).strip()

    # Extract action with coordinates
    action_match = re.search(
        r"Action:\s*(\w+)\s*\(\s*(?:start_box|point|box)\s*=\s*['\"]?\(?\s*(\d+)\s*,\s*(\d+)\s*\)?['\"]?\s*\)",
        text,
        re.IGNORECASE,
    )

    if action_match:
        action_type = action_match.group(1).lower()
        raw_x = int(action_match.group(2))
        raw_y = int(action_match.group(3))

        # Convert normalized 0-1000 coords to actual pixels
        pixel_x, pixel_y = _normalize_to_pixels(raw_x, raw_y, screen_w, screen_h)
        log.info("Coordinate conversion: (%d,%d)/1000 -> (%d,%d)px on %dx%d",
                 raw_x, raw_y, pixel_x, pixel_y, screen_w, screen_h)

        action_map = {
            "click": "click",
            "left_click": "click",
            "right_click": "click",
            "double_click": "click",
            "type": "type",
            "hotkey": "key",
            "scroll": "wait",
            "move": "wait",
            "screenshot": "wait",
            "done": "done",
        }

        return {
            "action": action_map.get(action_type, "click"),
            "x": pixel_x,
            "y": pixel_y,
            "reasoning": reasoning,
            "screen": reasoning[:80] if reasoning else action_type,
        }

    # Check for type action: Action: type(content='text here')
    type_match = re.search(
        r"Action:\s*type\s*\(\s*(?:content|text)\s*=\s*['\"](.+?)['\"]",
        text,
        re.IGNORECASE,
    )
    if type_match:
        return {
            "action": "type",
            "text": type_match.group(1),
            "reasoning": reasoning,
            "screen": reasoning[:80] if reasoning else "type",
        }

    # Check for hotkey action: Action: hotkey(key='enter')
    key_match = re.search(
        r"Action:\s*(?:hotkey|key|press)\s*\(\s*(?:key|keys)\s*=\s*['\"](.+?)['\"]",
        text,
        re.IGNORECASE,
    )
    if key_match:
        return {
            "action": "key",
            "key": key_match.group(1),
            "reasoning": reasoning,
            "screen": reasoning[:80] if reasoning else "key",
        }

    # Check for done action
    if re.search(r"Action:\s*done\s*\(\s*\)", text, re.IGNORECASE):
        return {
            "action": "done",
            "at_desktop": True,
            "reasoning": reasoning,
            "screen": "desktop",
        }

    # JSON fallback
    json_match = re.search(r"\{[^{}]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    log.warning("Could not parse UI-TARS response: %s", text[:200])
    return {"action": "wait", "reasoning": f"Could not parse response: {text[:100]}"}


def analyze_screen(llm: Llama, screenshot_b64: str, screen_size: tuple[int, int], ui_elements: list = None) -> dict:
    """Send screenshot to UI-TARS and get the action to perform."""
    w, h = screen_size

    prompt = f"""{SYSTEM_PROMPT}

The screen is {w}x{h} pixels. Output coordinates in the 0-1000 normalized range.

Analyze the screenshot and determine the next action to automate Windows OOBE setup.

Output format:
Thought: [your reasoning about what you see and what to do]
Action: click(start_box='(X,Y)')
"""

    image_url = f"data:image/jpeg;base64,{screenshot_b64}"

    try:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
            max_tokens=512,
            temperature=0.1,
        )

        raw = response["choices"][0]["message"]["content"].strip()
        log.info("Raw UI-TARS response: %s", raw[:500])

        action = parse_ui_tars_response(raw, screen_size)

        # Check if we've reached desktop
        if action.get("action") == "done" or action.get("at_desktop"):
            action["at_desktop"] = True
        elif "desktop" in raw.lower() and "taskbar" in raw.lower():
            action["at_desktop"] = True

        log.info(
            "Parsed action: action=%s x=%s y=%s reason=%s",
            action.get("action"),
            action.get("x"),
            action.get("y"),
            action.get("reasoning", "")[:100],
        )
        return action

    except Exception as e:
        log.error("UI-TARS inference error: %s", e)
        return {"action": "wait", "reasoning": f"Inference error: {e}"}
