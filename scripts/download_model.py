"""Download UI-TARS 1.5 7B GGUF model files from HuggingFace.

UI-TARS is a vision-language model specifically trained for GUI automation
with accurate coordinate prediction for UI elements.
"""

import os
from huggingface_hub import hf_hub_download

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

# UI-TARS 1.5 7B — Q4_K quantization (~4-5GB)
MODEL_REPO = "Mungert/UI-TARS-1.5-7B-GGUF"
MODEL_FILE = "UI-TARS-1.5-7B-q4_k.gguf"
MODEL_LOCAL = "UI-TARS-1.5-7B-q4_k.gguf"

# Vision projector (mmproj) for UI-TARS
MMPROJ_REPO = "Mungert/UI-TARS-1.5-7B-GGUF"
MMPROJ_FILE = "UI-TARS-1.5-7B-q4_k.mmproj"
MMPROJ_LOCAL = "UI-TARS-1.5-7B-q4_k.mmproj"


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    model_path = os.path.join(MODELS_DIR, MODEL_LOCAL)
    mmproj_path = os.path.join(MODELS_DIR, MMPROJ_LOCAL)

    if not os.path.exists(model_path):
        print(f"Downloading {MODEL_FILE} from {MODEL_REPO}...")
        hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            local_dir=MODELS_DIR,
            local_dir_use_symlinks=False,
        )
        downloaded = os.path.join(MODELS_DIR, MODEL_FILE)
        os.rename(downloaded, model_path)
        print(f"Saved to {model_path}")
    else:
        print(f"Model already exists: {model_path}")

    if not os.path.exists(mmproj_path):
        print(f"Downloading {MMPROJ_FILE} from {MMPROJ_REPO}...")
        hf_hub_download(
            repo_id=MMPROJ_REPO,
            filename=MMPROJ_FILE,
            local_dir=MODELS_DIR,
            local_dir_use_symlinks=False,
        )
        downloaded = os.path.join(MODELS_DIR, MMPROJ_FILE)
        os.rename(downloaded, mmproj_path)
        print(f"Saved to {mmproj_path}")
    else:
        print(f"mmproj already exists: {mmproj_path}")

    print("Done! Model files ready in", MODELS_DIR)


if __name__ == "__main__":
    main()