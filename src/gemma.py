"""Gemma 4 E4B vision — runs locally via llama-cpp-python with bundled GGUF weights."""

import json
import logging

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

from config import MODEL_PATH, MMPROJ_PATH, MODEL_CTX_SIZE, MODEL_GPU_LAYERS, SYSTEM_PROMPT

log = logging.getLogger(__name__)


class GemmaVisionChatHandler(Llava15ChatHandler):
    """Llava15ChatHandler with Gemma's chat template instead of LLaVA's."""

    # Override the chat format to use Gemma's <start_of_turn> tokens
    # Images go BEFORE text per Google's recommendation
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
    """Load the bundled Gemma 4 E4B model with vision support."""
    log.info("Loading vision projector from %s", MMPROJ_PATH)
    chat_handler = GemmaVisionChatHandler(clip_model_path=MMPROJ_PATH, verbose=False)

    log.info("Loading model from %s", MODEL_PATH)
    llm = Llama(
        model_path=MODEL_PATH,
        chat_handler=chat_handler,
        n_ctx=MODEL_CTX_SIZE,
        n_gpu_layers=MODEL_GPU_LAYERS,
        n_ubatch=2048,  # Gemma 4 vision needs large ubatch for image tokens
        verbose=False,
    )
    log.info("Model loaded successfully")
    return llm


def analyze_screen(llm: Llama, screenshot_b64: str, screen_size: tuple[int, int], ui_elements: list = None) -> dict:
    """Send screenshot to Gemma and get the action to perform.
    
    Args:
        llm: Loaded Gemma model
        screenshot_b64: Base64-encoded screenshot
        screen_size: (width, height) of screen
        ui_elements: Optional list of UIElement objects from UI Automation
    """
    w, h = screen_size
    
    resolution_context = (
        f"The screen is {w}x{h} pixels. "
        f"Coordinate system: x ranges from 0 (left) to {w} (right), "
        f"y ranges from 0 (top) to {h} (bottom)."
    )
    
    # Import here to avoid circular dependency
    from uiauto import format_elements_for_prompt, get_clickable_elements
    
    # Format UI elements if available
    elements_context = ""
    clickable_elements = []
    if ui_elements:
        clickable_elements = get_clickable_elements(ui_elements)
        elements_context = format_elements_for_prompt(clickable_elements)
        if elements_context:
            resolution_context += "\n\n" + elements_context
    
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"{resolution_context}\n\n"
        "Look at the screenshot carefully."
    )
    
    if clickable_elements:
        prompt += " You have a list of UI elements above - USE element names when responding."
    else:
        prompt += " No UI elements available via automation - use screenshot analysis for coordinates."
    
    prompt += " Respond with ONLY a JSON object."

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
            temperature=0.3,
        )

        raw = response["choices"][0]["message"]["content"].strip()
        log.info("Raw Gemma response: %s", raw[:500])

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        # Find JSON object
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]

        action = json.loads(raw)
        
        # Attach UI elements to action for automator to use
        if clickable_elements:
            action["_ui_elements"] = clickable_elements
        
        log.info("Parsed action: screen=%s action=%s target=%s", 
                 action.get("screen"), action.get("action"), action.get("target"))
        return action

    except json.JSONDecodeError as e:
        log.error("Failed to parse JSON: %s\nRaw: %s", e, raw)
        return {"action": "wait", "reasoning": "Failed to parse response"}
    except Exception as e:
        log.error("Gemma inference error: %s", e)
        return {"action": "wait", "reasoning": f"Inference error: {e}"}
