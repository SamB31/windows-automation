"""Gemma 3 4B vision integration via ollama."""

import json
import logging

import ollama

from config import MODEL_NAME, OLLAMA_HOST, SYSTEM_PROMPT

log = logging.getLogger(__name__)


def create_client() -> ollama.Client:
    """Create an ollama client pointing at the configured host."""
    return ollama.Client(host=OLLAMA_HOST)


def analyze_screen(client: ollama.Client, screenshot_b64: str, screen_size: tuple[int, int]) -> dict:
    """Send screenshot to Gemma and get the action to perform.

    Args:
        client: ollama client instance
        screenshot_b64: base64-encoded JPEG screenshot
        screen_size: (width, height) of the screenshot

    Returns:
        Parsed action dict from Gemma's response
    """
    prompt = (
        f"Screenshot dimensions: {screen_size[0]}x{screen_size[1]}. "
        "Analyze this Windows OOBE screenshot and tell me what action to take next. "
        "Respond ONLY with valid JSON."
    )

    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": prompt,
                    "images": [screenshot_b64],
                },
            ],
        )

        raw = response.message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        action = json.loads(raw)
        log.info("Gemma analysis: %s -> %s", action.get("screen"), action.get("action"))
        return action

    except json.JSONDecodeError as e:
        log.error("Failed to parse Gemma response as JSON: %s\nRaw: %s", e, raw)
        return {"action": "wait", "reasoning": "Failed to parse response"}
    except Exception as e:
        log.error("Gemma API error: %s", e)
        return {"action": "wait", "reasoning": f"API error: {e}"}
