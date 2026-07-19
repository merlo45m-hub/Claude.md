# Conversation Memory - Persistent

## Environment
- VPS: 16GB RAM, 240GB storage
- Access: Samsung Galaxy S26 Ultra via Termius SSH client
- Date: 2026-07-14

## Projects
- **Roblox Math Quest**: Godot Engine project at `/root/roblox-math-quest`
- **AI Stock Trading Bot**: `/root/ai_stock_trader`

## Previous Work
1. Checked file locations for Godot project files
2. Found actual paths:
   - GameManager.gd: `roblox-math-quest/Autoload/GameManager.gd`
   - SaveManager.gd: `roblox-math-quest/Autoload/SaveManager.gd`
   - Roadblock.gd: `roblox-math-quest/scripts/Roadblock.gd`
3. Created checkpoint copies in `checkpoint/` directory
4. Encountered read_file tool error (DaemonThreadPoolExecutor issue)
5. Used terminal `cp` to copy files successfully

## Recovery Steps
- If session crashes, check `/root/roblox-math-quest/checkpoint/` for file copies
- STATE_SNAPSHOT.md has full recovery instructions
- Git not initialized - recommend adding for future resilience

## Tools Used
- read_file: failed with internal API error
- terminal cp: successful
- search_files: found file locations