# Windows OOBE Automation

## Project Overview
Automates Windows Out-of-Box Experience (OOBE) using Google Gemma 4 E4B vision model.
The program captures screenshots, analyzes them with Gemma, and performs keyboard/mouse
actions to navigate through OOBE screens until reaching the desktop, then runs an
initialization script.

**Key constraint: the exe must be 100% self-contained.** The target machine is a fresh
Windows install at OOBE — nothing is pre-installed. The GGUF model weights, vision
projector, and inference engine (llama.cpp) are all bundled into the single exe.

## Architecture
- **Entry point**: `src/main.py` — main loop: screenshot → analyze → act → repeat
- **Screenshot**: `src/screenshot.py` — screen capture via `mss`
- **Vision AI**: `src/gemma.py` — Gemma 4 E4B via `llama-cpp-python` with bundled GGUF weights
- **Automation**: `src/automator.py` — keyboard/mouse control via `pyautogui`
- **Overlay**: `src/overlay.py` — rainbow ring overlay using `pygame` (runs in separate thread)
- **Config**: `src/config.py` — settings, resource paths (handles PyInstaller `_MEIPASS`)

## Model Files
Download before building:
```bash
python scripts/download_model.py
```
This downloads to `models/`:
- `gemma-4-E4B-it.gguf` (~5.4GB, Q4_K_M quantized from bartowski)
- `gemma-4-E4B-it-mmproj.gguf` (~990MB, F16 vision projector from unsloth)

## Build
```bash
python -m pip install -r requirements.txt
python scripts/download_model.py
pyinstaller --onefile --noconsole --name oobe-automator \
  --add-data "models/gemma-4-E4B-it.gguf;." \
  --add-data "models/gemma-4-E4B-it-mmproj.gguf;." \
  src/main.py
```
Output: `dist/oobe-automator.exe` (~6.5GB self-contained)

## Testing on Proxmox
- Server: `ssh -i ~/.ssh/proxmox root@10.1.0.10`
- Test VM: VMID 200 ("OOBE-Test"), Windows 11 25H2, 16GB RAM
- OOBE snapshot: `qm snapshot 200 oobe-start`
- Restore: `qm rollback 200 oobe-start`
- SCP exe to host: `scp -i ~/.ssh/proxmox dist/oobe-automator.exe root@10.1.0.10:/tmp/`
- During OOBE: Shift+F10 opens cmd, then run the exe from a network share or mounted disk

## Key Dependencies
- `llama-cpp-python` — llama.cpp Python bindings (bundles inference engine)
- `mss` — fast cross-platform screenshots
- `pyautogui` — keyboard/mouse automation
- `Pillow` — image processing
- `pygame` — overlay rendering
- `pyinstaller` — exe packaging
- `huggingface-hub` — model download
