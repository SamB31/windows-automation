# Build & Deploy Guide

## Prerequisites

- Python 3.13+ on Windows
- SSH key at `~/.ssh/proxmox` with access to Proxmox nodes
- ~12GB free disk space for model files + build output

## 1. Set Up Virtual Environment

```bash
cd windows-automation
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Required packages: `mss`, `pyautogui`, `Pillow`, `llama-cpp-python`, `pygame`, `pyinstaller`, `huggingface-hub`

## 2. Download Model Files

```bash
python scripts/download_model.py
```

This downloads from HuggingFace into `models/`:
- `gemma-4-E4B-it.gguf` (~5.4GB) — Q4_K_M quantization from [bartowski](https://huggingface.co/bartowski/google_gemma-4-E4B-it-GGUF)
- `gemma-4-E4B-it-mmproj.gguf` (~945MB) — F16 vision projector from [unsloth](https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF)

## 3. Split Model for PyInstaller

PyInstaller's `--onefile` archive format has a 4GB per-file limit. Since the model is 5.4GB, we split it into chunks that get reassembled at runtime.

```bash
python scripts/split_model.py
```

This creates in `models/`:
- `gemma-4-E4B-it.gguf.part0` (3GB)
- `gemma-4-E4B-it.gguf.part1` (~2.4GB)
- `manifest.json` (maps original filenames to their chunks)

The mmproj file (~945MB) is under 4GB so it stays as-is.

**Note:** We use `--onedir` mode (not `--onefile`) because even the chunked files plus DLLs exceed the 4GB total archive limit. The `--onedir` output is then packaged into an ISO for delivery.

## 4. Build the Exe

```bash
.venv/Scripts/pyinstaller.exe --onedir --noconsole --name oobe-automator \
  --add-data "models/gemma-4-E4B-it.gguf.part0;." \
  --add-data "models/gemma-4-E4B-it.gguf.part1;." \
  --add-data "models/gemma-4-E4B-it-mmproj.gguf;." \
  --add-data "models/manifest.json;." \
  --paths src \
  --hidden-import llama_cpp \
  --collect-all llama_cpp \
  src/main.py
```

Output: `dist/oobe-automator/` directory (~6.2GB) containing:
- `oobe-automator.exe` — main executable (~17MB)
- `_internal/` — Python runtime, DLLs, model chunks, mmproj, manifest

### What each flag does:
- `--onedir` — creates a directory (not a single file) to avoid the 4GB archive limit
- `--noconsole` — no console window (overlay + log file handle output)
- `--add-data "file;."` — bundles each file into the root of `_internal/`
- `--paths src` — adds `src/` to the Python import path so modules find each other
- `--hidden-import llama_cpp` — ensures llama_cpp is included (not always auto-detected)
- `--collect-all llama_cpp` — includes all llama_cpp submodules and shared libraries (.dll/.so)

### Runtime behavior:
When `oobe-automator.exe` launches, `config.py` checks for `manifest.json` in the `_internal/` directory. If the model was split, it reassembles the chunks into `%TEMP%/oobe-automator/gemma-4-E4B-it.gguf` before loading. This only happens on first run — subsequent runs reuse the reassembled file.

## 5. Upload to Proxmox and Create ISO

The VM runs from a mounted ISO (CD/DVD drive) since the OOBE environment has no writable USB or network share access.

### Clean the remote directory and upload:

```bash
ssh -i ~/.ssh/proxmox root@10.1.0.12 "rm -rf /tmp/oobe-automator"
scp -i ~/.ssh/proxmox -r dist/oobe-automator root@10.1.0.12:/tmp/oobe-automator
```

### Create the ISO on the Proxmox host:

```bash
ssh -i ~/.ssh/proxmox root@10.1.0.12 \
  "rm -f /var/lib/vz/template/iso/oobe-automator.iso && \
   genisoimage -o /var/lib/vz/template/iso/oobe-automator.iso \
     -J -r -V OOBE-AUTOMATOR /tmp/oobe-automator/"
```

- `-J` — Joliet extensions (Windows-compatible long filenames)
- `-r` — Rock Ridge extensions (preserves Unix permissions)
- `-V OOBE-AUTOMATOR` — volume label (shows up as drive name in Windows)

The ISO lands at `/var/lib/vz/template/iso/oobe-automator.iso` (~6.2GB) and is immediately available in the Proxmox UI under the `local` storage ISO list.

### One-liner for steps 5:

```bash
ssh -i ~/.ssh/proxmox root@10.1.0.12 "rm -rf /tmp/oobe-automator" && \
scp -i ~/.ssh/proxmox -r dist/oobe-automator root@10.1.0.12:/tmp/oobe-automator && \
ssh -i ~/.ssh/proxmox root@10.1.0.12 \
  "rm -f /var/lib/vz/template/iso/oobe-automator.iso && \
   genisoimage -o /var/lib/vz/template/iso/oobe-automator.iso \
     -J -r -V OOBE-AUTOMATOR /tmp/oobe-automator/ && \
   echo 'ISO replaced'"
```

## 6. Attach ISO and Test

1. In the Proxmox UI, go to VM 200 → Hardware
2. Add a CD/DVD drive pointing to `oobe-automator.iso`
3. Rollback to the `oobe-start` snapshot: `qm rollback 200 oobe-start`
4. Start the VM: `qm start 200`
5. Open the console (noVNC), press **Shift+F10** at the OOBE screen to open a command prompt
6. Run the exe from the CD drive:

```
F:\oobe-automator.exe
```

If F: isn't the right drive letter, check with:
```
wmic logicaldisk get name,description
```

## 7. Reading Logs from the VM

The log file is at `%TEMP%\oobe-automator.log` inside the VM. You can read it:

**From inside the VM** (cmd prompt):
```
type %TEMP%\oobe-automator.log
```

**From the Proxmox host** (mount the VM disk read-only):
```bash
mount -t ntfs3 -o ro,offset=122683392 /dev/pve/vm-200-disk-1 /mnt/vm200
cat /mnt/vm200/Users/defaultuser0/AppData/Local/Temp/oobe-automator.log
umount /mnt/vm200
```

The offset `122683392` is the byte offset of the Windows NTFS partition (sector 239616 × 512). If the partition layout changes, recalculate with:
```bash
fdisk -l /dev/pve/vm-200-disk-1 | grep "Microsoft basic data"
# Multiply the Start sector by 512
```

## Full Rebuild + Deploy Script

```bash
cd windows-automation

# Build
rm -rf build dist oobe-automator.spec
.venv/Scripts/pyinstaller.exe --onedir --noconsole --name oobe-automator \
  --add-data "models/gemma-4-E4B-it.gguf.part0;." \
  --add-data "models/gemma-4-E4B-it.gguf.part1;." \
  --add-data "models/gemma-4-E4B-it-mmproj.gguf;." \
  --add-data "models/manifest.json;." \
  --paths src --hidden-import llama_cpp --collect-all llama_cpp \
  src/main.py

# Deploy
ssh -i ~/.ssh/proxmox root@10.1.0.12 "rm -rf /tmp/oobe-automator"
scp -i ~/.ssh/proxmox -r dist/oobe-automator root@10.1.0.12:/tmp/oobe-automator
ssh -i ~/.ssh/proxmox root@10.1.0.12 \
  "rm -f /var/lib/vz/template/iso/oobe-automator.iso && \
   genisoimage -o /var/lib/vz/template/iso/oobe-automator.iso \
     -J -r -V OOBE-AUTOMATOR /tmp/oobe-automator/"

# Test
ssh -i ~/.ssh/proxmox root@10.1.0.12 "qm rollback 200 oobe-start && qm start 200"
```
