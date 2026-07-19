# roblox-math-quest

type: godot 4 game (android export)
state: GameManager {xp, coins, level, streak, accuracy}
persist: SaveManager -> user://save.dat (json)

SCENES
  Main.tscn ............ UI root, binds GameManager autoload
  Roadblock.tscn ....... math problem gate
  MiniGames/TapNumbers.tscn ... fires every 4 roadblocks (MINIGAME_INTERVAL)

FLOW
  answer correct -> emit_signals -> UI refresh

BUILD
  godot editor -> export_presets.cfg -> builds/android_{debug,release}.apk

NOTES
  - no server, no db, no running service
  - game-devops handled in a separate hermes profile
  - difficulty scales with level
