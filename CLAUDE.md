# Windows OOBE Automation

## Project Overview
Automates Windows Out-of-Box Experience (OOBE) using Google Gemma 3 4B vision model.
The program captures screenshots, analyzes them with Gemma, and performs keyboard/mouse
actions to navigate through OOBE screens until reaching the desktop, then runs an
initialization script.

## Architecture
- **Entry point**: `src/main.py` — main loop: screenshot → analyze → act → repeat
- **Screenshot**: `src/screenshot.py` — screen capture via `mss`
- **Vision AI**: `src/gemma.py` — Gemma 3 4B via `ollama` Python client (supports remote endpoint)
- **Automation**: `src/automator.py` — keyboard/mouse control via `pyautogui`
- **Overlay**: `src/overlay.py` — rainbow ring overlay using `pygame` (runs in separate thread)
- **Config**: `src/config.py` — settings (ollama endpoint, timings, etc.)

## Build
```bash
python -m pip install -r requirements.txt
pyinstaller --onefile --noconsole --name oobe-automator src/main.py
```
Output: `dist/oobe-automator.exe`

## Testing on Proxmox
- Server: `ssh -i ~/.ssh/proxmox root@10.1.0.10`
- Test VM: VMID 200 ("OOBE-Test"), Windows 11 25H2
- OOBE snapshot: `qm snapshot 200 oobe-start`
- Restore: `qm rollback 200 oobe-start`
- SCP exe to host: `scp -i ~/.ssh/proxmox dist/oobe-automator.exe root@10.1.0.10:/tmp/`
- During OOBE: Shift+F10 opens cmd, then run the exe from a network share or mounted disk

## Gemma Endpoint
For testing, run ollama on the Proxmox host or local machine:
```bash
ollama pull gemma3:4b
ollama serve  # listens on 0.0.0.0:11434
```
The exe connects to the ollama API endpoint (configurable via `OLLAMA_HOST` env var).

## Key Dependencies
- `mss` — fast cross-platform screenshots
- `pyautogui` — keyboard/mouse automation
- `Pillow` — image processing
- `ollama` — Python client for ollama API
- `pygame` — overlay rendering
- `pyinstaller` — exe packaging
