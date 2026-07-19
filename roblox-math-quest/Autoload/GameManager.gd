# Autoload/GameManager.gd
extends Node

# Signals
signal xp_changed(amount)
signal coins_changed(amount)
signal level_changed(new_level)
signal achievement_unlocked(achievement_id)

# Config
const XP_PER_CORRECT := 10
const COINS_PER_CORRECT := 5
const XP_PER_LEVEL := 100  # base, can increase per level
const MINIGAME_INTERVAL := 4  # every N roadblocks

# State
var xp := 0
var coins := 0
var level := 1
var streak := 0
var total_roadblocks := 0
var correct_answers := 0
var wrong_answers := 0
var accuracy := 0.0
var minigame_counter := 0

# Difficulty adjustment
var difficulty := 1.0  # multiplier for number ranges
var accuracy_window := []  # last N accuracies for smoothing
const ACCURACY_WINDOW_SIZE := 5

# Achievements data structure
var achievements := [
    {"id": "first_correct", "name": "First Steps", "desc": "Answer your first problem correctly", "icon": "res://icons/achievements/first_correct.png", "condition": "first_correct"},
    {"id": "streak_5", "name": "On Fire!", "desc": "Get a 5-answer streak", "icon": "res://icons/achievements/streak_5.png", "condition": "streak_5"},
    {"id": "level_5", "name": "Level 5", "desc": "Reach level 5", "icon": "res://icons/achievements/level_5.png", "condition": "level_5"},
    {"id": "coins_100", "name": "Piggy Bank", "desc": "Collect 100 coins", "icon": "res://icons/achievements/coins_100.png", "condition": "coins_100"},
]

func _ready() -> void:
    # Load saved data
    var save_manager := Autoload.get_singleton("SaveManager")
    if save_manager:
        save_manager.load_data()
    # Update accuracy
    _update_accuracy()
    # Emit initial signals
    emit_signal("xp_changed", xp)
    emit_signal("coins_changed", coins)
    emit_signal("level_changed", level)

func add_correct_answer() -> void:
    correct_answers += 1
    streak += 1
    total_roadblocks += 1
    minigame_counter += 1
    xp += XP_PER_CORRECT * difficulty
    coins += COINS_PER_CORRECT
    _update_accuracy()
    _check_level_up()
    _check_achievements()
    emit_signal("xp_changed", XP_PER_CORRECT * difficulty)
    emit_signal("coins_changed", COINS_PER_CORRECT)
    # Optional: haptic feedback
    if OS.get_name() in ["Android", "iOS"]:
        Input.vibrate_handheld(0.1)

func add_wrong_answer() -> void:
    wrong_answers += 1
    streak = 0  # reset streak on wrong
    total_roadblocks += 1
    minigame_counter += 1
    _update_accuracy()
    _check_achievements()  # maybe none for wrong
    # Optional: haptic feedback
    if OS.get_name() in ["Android", "iOS"]:
        Input.vibrate_handheld(0.05, 0.05)  # two short pulses

func _update_accuracy() -> void:
    if total_roadblocks > 0:
        accuracy = correct_answers / total_roadblocks
    else:
        accuracy = 0.0
    accuracy_window.append(accuracy)
    if accuracy_window.size() > ACCURACY_WINDOW_SIZE:
        accuracy_window.pop_front()
    var avg_accuracy := 0.0
    for a in accuracy_window:
        avg_accuracy += a
    avg_accuracy /= max(1, accuracy_window.size())
    # Adjust difficulty: if accuracy > 0.8 increase, < 0.5 decrease
    if avg_accuracy > 0.8:
        difficulty = min(difficulty + 0.05, 2.0)  # cap
    elif avg_accuracy < 0.5:
        difficulty = max(difficulty - 0.05, 0.5)  # floor

func _check_level_up() -> void:
    var new_level := floor(xp / XP_PER_LEVEL) + 1
    if new_level > level:
        level = new_level
        emit_signal("level_changed", level)
        # TODO: trigger level-up animation via signal to main scene
        # Optional: haptic feedback
        if OS.get_name() in ["Android", "iOS"]:
            Input.vibrate_handheld(0.2)

func _check_achievements() -> void:
    for ach in achievements:
        if not ach.get("unlocked", false):
            var condition := ach["condition"]
            var unlocked := false
            match condition:
                "first_correct":
                    unlocked = (correct_answers >= 1)
                "streak_5":
                    unlocked = (streak >= 5)
                "level_5":
                    unlocked = (level >= 5)
                "coins_100":
                    unlocked = (coins >= 100)
            if unlocked:
                ach["unlocked"] = true
                emit_signal("achievement_unlocked", ach["id"])
                # Optional: give reward
                coins += 10
                emit_signal("coins_changed", 10)

func get_minigame_required() -> bool:
    return minigame_counter >= MINIGAME_INTERVAL

func reset_minigame_counter() -> void:
    minigame_counter = 0

func get_stats() -> Dictionary:
    return {
        "xp": xp,
        "coins": coins,
        "level": level,
        "streak": streak,
        "accuracy": accuracy,
        "correct": correct_answers,
        "wrong": wrong_answers,
        "total": total_roadblocks
    }

func save_data() -> void:
    var save_manager := Autoload.get_singleton("SaveManager")
    if save_manager:
        save_manager.save_data({
            "xp": xp,
            "coins": coins,
            "level": level,
            "streak": streak,
            "correct_answers": correct_answers,
            "wrong_answers": wrong_answers,
            "achievements": achievements
        })

func load_data(data: Dictionary) -> void:
    xp = data.get("xp", 0)
    coins = data.get("coins", 0)
    level = data.get("level", 1)
    streak = data.get("streak", 0)
    correct_answers = data.get("correct_answers", 0)
    wrong_answers = data.get("wrong_answers", 0)
    # achievements may be list of dicts; we assume same order
    var saved_ach := data.get("achievements", [])
    for i in range(min(achievements.size(), saved_ach.size())):
        achievements[i]["unlocked"] = saved_ach[i].get("unlocked", false)
    _update_accuracy()
    emit_signal("xp_changed", xp)
    emit_signal("coins_changed", coins)
    emit_signal("level_changed", level)

func get_xp_for_next_level() -> int:
    return XP_PER_LEVEL * level

func get_current_xp() -> int:
    return xp

func get_current_level() -> int:
    return level

func get_current_coins() -> int:
    return coins

func get_current_streak() -> int:
    return streak

func add_xp(amount: int) -> void:
    xp += amount
    _check_level_up()

func add_coins(amount: int) -> void:
    coins += amount
    emit_signal("coins_changed", amount)

func increment_streak() -> void:
    streak += 1

func reset_streak() -> void:
    streak = 0

func level_up() -> void:
    level += 1
    emit_signal("level_changed", level)

func get_xp_per_correct() -> int:
    return XP_PER_CORRECT

func get_coins_per_correct() -> int:
    return COINS_PER_CORRECT

func get_minigame_interval() -> int:
    return MINIGAME_INTERVAL

func is_achievement_unlocked(achievement_id: String) -> bool:
    for ach in achievements:
        if ach["id"] == achievement_id:
            return ach.get("unlocked", false)
    return false