# Autoload/SaveManager.gd
extends Node

const SAVE_FILE := "user://save.dat"
const DEFAULT_DATA := {
    "xp": 0,
    "coins": 0,
    "level": 1,
    "streak": 0,
    "correct_answers": 0,
    "wrong_answers": 0,
    "achievements": []  # list of dicts with "id" and "unlocked" bool
}

func _ready() -> void:
    pass

func save_data(data: Dictionary) -> void:
    var file = File.new()
    if file.open(SAVE_FILE, File.WRITE) != OK:
        push_error("Cannot open save file for writing: %s" % SAVE_FILE)
        return
    var json_str = JSON.stringify(data)
    file.store_string(json_str)
    file.close()

func load_data() -> Dictionary:
    var file = File.new()
    if file.open(SAVE_FILE, File.READ) != OK:
        # No save file, return default
        return DEFAULT_DATA.deep_copy()
    var json_str = file.get_as_text()
    file.close()
    var result = JSON.parse(json_str)
    if result.error != OK:
        push_error("Failed to parse save data: %s" % result.error_string)
        return DEFAULT_DATA.deep_copy()
    # Ensure we have all default keys (in case save file is old)
    var data = result.result
    for key in DEFAULT_DATA.keys():
        if not data.has(key):
            data[key] = DEFAULT_DATA[key]
    return data

func clear_save() -> void:
    var dir = Directory.new()
    dir.remove(SAVE_FILE)