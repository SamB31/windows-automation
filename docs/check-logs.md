# Checking OOBE Automator Logs

## Quick Reference

```bash
# 1. Mount the VM disk (read-only, offset to NTFS partition)
ssh -i ~/.ssh/proxmox root@10.1.0.12 "mkdir -p /mnt/vm200 && mount -t ntfs3 -o ro,offset=122683392 /dev/pve/vm-200-disk-1 /mnt/vm200"

# 2. Find and read the log file
ssh -i ~/.ssh/proxmox root@10.1.0.12 "find /mnt/vm200/Users -name 'oobe-automator.log' -type f"

# 3. Read the full log
ssh -i ~/.ssh/proxmox root@10.1.0.12 "cat /mnt/vm200/Users/defaultuser0/AppData/Local/Temp/oobe-automator.log"

# 4. Read last 100 lines
ssh -i ~/.ssh/proxmox root@10.1.0.12 "tail -100 /mnt/vm200/Users/defaultuser0/AppData/Local/Temp/oobe-automator.log"

# 5. Unmount when done
ssh -i ~/.ssh/proxmox root@10.1.0.12 "umount /mnt/vm200"
```

## One-liner for latest log
```bash
ssh -i ~/.ssh/proxmox root@10.1.0.12 "cat /mnt/vm200/Users/defaultuser0/AppData/Local/Temp/oobe-automator.log 2>/dev/null || cat /mnt/vm200/Users/*/AppData/Local/Temp/oobe-automator.log"
```

## Notes
- VM must be running to mount
- offset=122683392 points to the NTFS partition start
- defaultuser0 is the Windows OOBE default user
- Log path: `%TEMP%\oobe-automator.log`