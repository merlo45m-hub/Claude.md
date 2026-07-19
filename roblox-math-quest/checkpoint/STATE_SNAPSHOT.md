# Roblox Math Quest — Checkpoint Snapshot
Date: 2026-07-14 20:36 UTC
VPS: 16GB RAM, 240GB storage
Access: Samsung Galaxy S26 Ultra via Termius (SSH)

## Project Structure
- /root/roblox-math-quest/ (Godot project)
  - roblox-math-quest/ (nested — project root)
    - Autoload/GameManager.gd, SaveManager.gd
    - scripts/Roadblock.gd
    - Roadblock.tscn, project.godot

## Checkpointed Files (copies saved in ./checkpoint/)
- GameManager.gd
- SaveManager.gd
- Roadblock.gd

## How to Resume After Crash
1. SSH into VPS via Termius (same host/IP, key or password)
2. cd /root/roblox-math-quest/roblox-math-quest
3. Open Godot Editor on VPS or locally
4. Files are safe — checkpoint/ holds copies if main gets corrupted

## Notes
- read_file tool had internal API error ('DaemonThreadPoolExecutor') — used cp via terminal instead
- MemPalace auto-checkpoint configured via AGENTS.md
