"""Download Gemma 4 E4B GGUF model files from HuggingFace."""

import os
from huggingface_hub import hf_hub_download

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

# Gemma 4 E4B Instruct — Q4_K_M quantized by Bartowski (~5.4GB)
MODEL_REPO = "bartowski/google_gemma-4-E4B-it-GGUF"
MODEL_FILE = "google_gemma-4-E4B-it-Q4_K_M.gguf"
MODEL_LOCAL = "gemma-4-E4B-it.gguf"

# Vision projector (mmproj) from Unsloth (~990MB)
MMPROJ_REPO = "unsloth/gemma-4-E4B-it-GGUF"
MMPROJ_FILE = "mmproj-F16.gguf"
MMPROJ_LOCAL = "gemma-4-E4B-it-mmproj.gguf"


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
