"""Split model files into <4GB chunks for PyInstaller bundling.

PyInstaller --onefile has a 4GB per-file limit (32-bit archive format).
This splits large GGUF files into chunks and creates a manifest for reassembly.
"""

import json
import os

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
CHUNK_SIZE = 3 * 1024 * 1024 * 1024  # 3GB chunks (well under 4GB limit)


def split_file(filepath: str) -> list[str]:
    """Split a file into chunks. Returns list of chunk filenames."""
    filesize = os.path.getsize(filepath)
    if filesize <= CHUNK_SIZE:
        print(f"  {os.path.basename(filepath)} is under {CHUNK_SIZE // (1024**3)}GB, no split needed")
        return [os.path.basename(filepath)]

    basename = os.path.basename(filepath)
    chunks = []
    with open(filepath, "rb") as f:
        part = 0
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            chunk_name = f"{basename}.part{part}"
            chunk_path = os.path.join(os.path.dirname(filepath), chunk_name)
            with open(chunk_path, "wb") as out:
                out.write(data)
            chunks.append(chunk_name)
            print(f"  Wrote {chunk_name} ({len(data) / (1024**3):.2f}GB)")
            part += 1

    return chunks


def main():
    manifest = {}

    for name in ["gemma-4-E4B-it.gguf", "gemma-4-E4B-it-mmproj.gguf"]:
        filepath = os.path.join(MODELS_DIR, name)
        if not os.path.exists(filepath):
            print(f"Skipping {name} (not found)")
            continue
        print(f"Processing {name}...")
        chunks = split_file(filepath)
        manifest[name] = chunks

    manifest_path = os.path.join(MODELS_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written to {manifest_path}")
    print("Chunks ready for PyInstaller bundling")


if __name__ == "__main__":
    main()
