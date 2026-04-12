"""UI-TARS vision — runs locally via llama-cpp-python with bundled GGUF weights.

UI-TARS is specifically trained for GUI agent tasks with accurate coordinate prediction.
Unlike general VLMs (like Gemma), UI-TARS understands UI elements and can accurately
locate them on screen.
"""

import json
import logging
import re
from typing import Optional

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

from config import (
    MODEL_PATH,
    MMPROJ_PATH,
    MODEL_CTX_SIZE,
    MODEL_GPU_LAYERS,
    SYSTEM_PROMPT,
)

log = logging.getLogger(__name__)


class UI_TARS_ChatHandler(Llava15ChatHandler):
    """Llava15ChatHandler with UI-TARS chat template."""

    CHAT_FORMAT = (
        "{% for message in messages %}"
        "{% if message.role == 'user' %}"
        "<start_of_turn>user\n"
        "{% if message.content is iterable and message.content is not string %}"
        "{% for content in message.content %}"
        "{% if content.type == 'image_url' and content.image_url is string %}"
        "{{ content.image_url }}"
        "{% endif %}"
        "{% if content.type == 'image_url' and content.image_url is mapping %}"
        "{{ content.image_url.url }}"
        "{% endif %}"
        "{% endfor %}"
        "{% for content in message.content %}"
        "{% if content.type == 'text' %}"
        "{{ content.text }}"
        "{% endif %}"
        "{% endfor %}"
        "{% else %}"
        "{{ message.content }}"
        "{% endif %}"
        "<end_of_turn>\n"
        "{% endif %}"
        "{% if message.role == 'assistant' and message.content is not none %}"
        "<start_of_turn>model\n"
        "{{ message.content }}"
        "<end_of_turn>\n"
        "{% endif %}"
        "{% endfor %}"
        "{% if add_generation_prompt %}"
        "<start_of_turn>model\n"
        "{% endif %}"
    )

    DEFAULT_SYSTEM_MESSAGE = None


def load_model() -> Llama:
    """Load the bundled UI-TARS model with vision support."""
    log.info("Loading vision projector from %s", MMPROJ_PATH)
    chat_handler = UI_TARS_ChatHandler(clip_model_path=MMPROJ_PATH, verbose=False)

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


def parse_ui_tars_response(text: str) -> dict:
    """Parse UI-TARS response into action dict.

    UI-TARS outputs actions like:
        Thought: reasoning text
        Action: click(start_box='(177,549)')

    Or sometimes just:
        Action: click(start_box='(177,549)')

    Returns dict like:
        {"action": "click", "x": 177, "y": 549, "reasoning": "..."}
    """
    reasoning = ""
    action_match = None

    # Extract thought/reasoning
    thought_match = re.search(r"Thought:\s*(.+?)(?:\nAction:|$)", text, re.IGNORECASE | re.DOTALL)
    if thought_match:
        reasoning = thought_match.group(1).strip()

    # Extract action
    action_match = re.search(
        r"Action:\s*(\w+)\s*\(\s*(?:start_box|point|box)\s*=\s*['\"]?\(?\s*(\d+)\s*,\s*(\d+)\s*\)?['\"]?\s*\)",
        text,
        re.IGNORECASE,
    )

    if action_match:
        action_type = action_match.group(1).lower()
        x = int(action_match.group(2))
        y = int(action_match.group(3))

        # Map UI-TARS action types to our format
        action_map = {
            "click": "click",
            "left_click": "click",
            "right_click": "click",
            "double_click": "double_click",
            "type": "type",
            "hotkey": "key",
            "scroll": "scroll",
            "move": "move",
            "screenshot": "screenshot",
            "done": "done",
        }

        action = action_map.get(action_type, "click")

        return {
            "action": action,
            "x": x,
            "y": y,
            "reasoning": reasoning,
        }

    # Check for JSON in response as fallback
    json_match = re.search(r"\{[^{}]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    log.warning("Could not parse UI-TARS response: %s", text[:200])
    return {"action": "wait", "reasoning": f"Could not parse response: {text[:100]}"}


def analyze_screen(llm: Llama, screenshot_b64: str, screen_size: tuple[int, int], ui_elements: list = None) -> dict:
    """Send screenshot to UI-TARS and get the action to perform.

    UI-TARS is trained specifically for GUI automation and provides accurate
    coordinate predictions compared to general VLMs.

    Args:
        llm: Loaded UI-TARS model
        screenshot_b64: Base64-encoded screenshot
        screen_size: (width, height) of screen
        ui_elements: Optional list of UIElement objects (not used with UI-TARS)

    Returns:
        action dict with keys: action, x, y, reasoning, at_desktop
    """
    w, h = screen_size

    resolution_context = (
        f"The screen is {w}x{h} pixels. "
        f"Coordinate system: x ranges from 0 (left) to {w} (right), "
        f"y ranges from 0 (top) to {h} (bottom). "
        f"IMPORTANT: Output accurate pixel coordinates for clicking."
    )

    prompt = f"""{SYSTEM_PROMPT}

{resolution_context}

Analyze the screenshot and determine the next action to automate Windows OOBE setup.

IMPORTANT: When you want to click something:
1. Provide the EXACT x,y pixel coordinates of the CENTER of the element
2. Use the coordinate system shown above
3. Think about where buttons typically appear in Windows OOBE dialogs

Output format:
Thought: [your reasoning about what you see and what to do]
Action: click(start_box='(X,Y)')  # Use actual pixel coordinates

Examples of good coordinates for 1280x800 screen:
- Yes/Accept buttons: typically (850, 520) or similar in bottom-right
- Country dropdown: typically (400, 300) in center-left
- Text fields: typically (400, 350) in center
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
            temperature=0.1,  # Lower temperature for more consistent coordinates
        )

        raw = response["choices"][0]["message"]["content"].strip()
        log.info("Raw UI-TARS response: %s", raw[:500])

        action = parse_ui_tars_response(raw)

        # Check if we've reached desktop
        if "done" in action.get("action", "").lower() or "desktop" in raw.lower():
            action["at_desktop"] = True
        elif "taskbar" in raw.lower() or "icons" in raw.lower():
            # Check if screen looks like desktop
            action["at_desktop"] = True

        log.info(
            "Parsed action: action=%s x=%s y=%s",
            action.get("action"),
            action.get("x"),
            action.get("y"),
        )
        return action

    except Exception as e:
        log.error("UI-TARS inference error: %s", e)
        return {"action": "wait", "reasoning": f"Inference error: {e}"}