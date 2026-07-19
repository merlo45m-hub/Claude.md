# Autoload/GameManager.gd
extends Node

# Signals
signal xp_changed(amount)
signal coins_changed(amount)
signal level_changed(new_level)
signal achievement_unlocked(achievement_id)
signal game_saved
signal game_loaded

# Constants
const XP_PER_CORRECT := 10
const COINS_PER_CORRECT := 5
const XP_PER_LEVEL_BASE := 100
const XP_PER_LEVEL_INCREASE_PER_LEVEL := 20  # Additional XP needed per level
const MINIGAME_INTERVAL := 4  # Every N roadblocks
const MAX_RETRIES := 2
const STREAK_BONUS_THRESHOLDS := [3, 5, 10, 15, 20]  # Streaks that give bonus coins

# Game state
var xp := 0
var coins := 0
var level := 1
var streak := 0
var total_roadblocks := 0
var correct_answers := 0
var wrong_answers := 0
var accuracy := 0.0
var minigame_counter := 0
var current_streak_bonus := 0

# Difficulty adjustment
var difficulty := 1.0  # Multiplier for number ranges
var accuracy_window := []  # Last N accuracies for smoothing
const ACCURACY_WINDOW_SIZE := 5
const DIFFICULTY_INCREASE_THRESHOLD := 0.8
const DIFFICULTY_DECREASE_THRESHOLD := 0.5
const DIFFICULTY_STEP := 0.05
const MAX_DIFFICULTY := 2.0
const MIN_DIFFICULTY := 0.5

# Achievements data structure
var achievements := [
    {"id": "first_correct", "name": "First Steps", "desc": "Answer your first problem correctly", "icon": "", "condition": FuncRef(self, "_check_first_correct"), "unlocked": false, "reward_coins": 10},
    {"id": "streak_5", "name": "On Fire!", "desc": "Get a 5-answer streak", "icon": "", "condition": FuncRef(self, "_check_streak_5"), "unlocked": false, "reward_coins": 20},
    {"id": "streak_10", "name": "Unstoppable!", "desc": "Get a 10-answer streak", "icon": "", "condition": FuncRef(self, "_check_streak_10"), "unlocked": false, "reward_coins": 50},
    {"id": "level_5", "name": "Level 5", "desc": "Reach level 5", "icon": "", "condition": FuncRef(self, "_check_level_5"), "unlocked": false, "reward_coins": 30},
    {"id": "level_10", "name": "Double Digits", "desc": "Reach level 10", "icon": "", "condition": FuncRef(self, "_check_level_10"), "unlocked": false, "reward_coins": 50},
    {"id": "coins_100", "name": "Piggy Bank", "desc": "Collect 100 coins", "icon": "", "condition": FuncRef(self, "_check_coins_100"), "unlocked": false, "reward_coins": 0},
    {"id": "coins_500", "name": "Treasure Hunter", "desc": "Collect 500 coins", "icon": "", "condition": FuncRef(self, "_check_coins_500"), "unlocked": false, "reward_coins": 0},
    {"id": "perfect_round", "name": "Perfectionist", "desc": "Complete 10 roadblocks with 100% accuracy", "icon": "", "condition": FuncRef(self, "_check_perfect_round"), "unlocked": false, "reward_coins": 75},
]

# Tracking for perfect round achievement
var perfect_round_count := 0
var perfect_round_in_progress := false

func _ready() -> void:
    # Load saved data
    var save_data := SaveManager.load_game()
    _apply_save_data(save_data)
    # Update UI
    _update_signals()
    # Start first perfect round tracking
    _start_perfect_round_tracking()

func _apply_save_data(data: Dictionary) -> void:
    xp = data.get("xp", 0)
    coins = data.get("coins", 0)
    level = data.get("level", 1)
    streak = data.get("streak", 0)
    total_roadblocks = data.get("total_roadblocks", 0)
    correct_answers = data.get("correct_answers", 0)
    wrong_answers = data.get("wrong_answers", 0)
    # Load achievements
    var saved_achievements := data.get("achievements", [])
    for i in range(min(achievements.size(), saved_achievements.size())):
        achievements[i]["unlocked"] = saved_achievements[i].get("unlocked", false)
    _update_accuracy()
    _update_difficulty()

func _update_accuracy() -> void:
    if total_roadblocks > 0:
        accuracy = correct_answers / total_roadblocks
    else:
        accuracy = 0.0
    
    # Update accuracy window for difficulty adjustment
    accuracy_window.append(accuracy)
    if accuracy_window.size() > ACCURACY_WINDOW_SIZE:
        accuracy_window.pop_front()
    
    # Adjust difficulty based on recent performance
    var avg_accuracy := 0.0
    if accuracy_window.size() > 0:
        for a in accuracy_window:
            avg_accuracy += a
        avg_accuracy /= accuracy_window.size()
    
    if avg_accuracy > DIFFICULTY_INCREASE_THRESHOLD:
        difficulty = min(difficulty + DIFFICULTY_STEP, MAX_DIFFICULTY)
    elif avg_accuracy < DIFFICULTY_DECREASE_THRESHOLD:
        difficulty = max(difficulty - DIFFICULTY_STEP, MIN_DIFFICULTY)

func _update_difficulty() -> void:
    # This is called whenever accuracy updates
    pass  # Logic is in _update_accuracy

func get_current_difficulty() -> float:
    return difficulty

func add_correct_answer() -> void:
    correct_answers += 1
    streak += 1
    total_roadblocks += 1
    minigame_counter += 1
    
    # Calculate XP and coins with streak bonus
    var base_xp := XP_PER_CORRECT * difficulty
    var base_coins := COINS_PER_CORRECT
    
    # Check for streak bonuses
    var streak_bonus := 0
    for threshold in STREAK_BONUS_THRESHOLDS:
        if streak >= threshold:
            streak_bonus += 5  # 5 extra coins per threshold passed
    
    var total_xp := int(base_xp)
    var total_coins := base_coins + streak_bonus
    
    xp += total_xp
    coins += total_coins
    current_streak_bonus = streak_bonus
    
    _update_accuracy()
    _check_level_up()
    _check_achievements()
    _update_signals()
    
    # Emit specific signals for UI
    emit_signal("xp_changed", total_xp)
    emit_signal("coins_changed", total_coins)
    
    # Check for perfect round achievement
    _check_perfect_round_progress(true)

func add_wrong_answer() -> void:
    wrong_answers += 1
    streak = 0  # Reset streak on wrong answer
    total_roadblocks += 1
    minigame_counter += 1
    
    _update_accuracy()
    _check_achievements()
    _update_signals()
    
    # Reset perfect round tracking
    _reset_perfect_round_tracking()

func _check_level_up() -> void:
    var xp_for_next_level := _get_xp_for_level(level + 1)
    if xp >= xp_for_next_level:
        level += 1
        emit_signal("level_changed", level)
        # Level up bonus
        coins += level * 10
        emit_signal("coins_changed", level * 10)
        # Reset difficulty slightly on level up to keep it challenging but fair
        difficulty = clamp(difficulty, MIN_DIFFICULTY, MAX_DIFFICULTY * 0.9)

func _get_xp_for_level(target_level: int) -> int:
    var xp := 0
    for lvl in range(1, target_level):
        xp += XP_PER_LEVEL_BASE + ((lvl - 1) * XPER_LEVEL_INCREASE)
    return xp

func _check_achievements() -> void:
    for ach in achievements:
        if not ach["unlocked"]:
            if ach["condition"].call_func():
                ach["unlocked"] = true
                emit_signal("achievement_unlocked", ach["id"])
                if ach["reward_coins"] > 0:
                    coins += ach["reward_coins"]
                    emit_signal("coins_changed", ach["reward_coins"])

# Achievement check methods
func _check_first_correct() -> bool:
    return correct_answers >= 1

func _check_streak_5() -> bool:
    return streak >= 5

func _check_streak_10() -> bool:
    return streak >= 10

func _check_level_5() -> bool:
    return level >= 5

func _check_level_10() -> bool:
    return level >= 10

func _check_coins_100() -> bool:
    return coins >= 100

func _check_coins_500() -> bool:
    return coins >= 500

func _check_perfect_round() -> bool:
    return perfect_round_count >= 1

func _start_perfect_round_tracking() -> void:
    perfect_round_in_progress_in_progress = true
    _reset_perfect_round_tracking()

func _reset_perfect_round_tracking() -> void:
    perfect_round_in_progress = false

func _check_perfect_round_progress(correct: bool) -> void:
    if not perfect_round_in_progress:
        return
    
    if not correct:
        _reset_perfect_round_tracking()
        return
    
    # Increment correct count in current perfect round attempt
    # We'd need to track this per round - for simplicity, let's track consecutive correct answers
    # Actually, let's redefine: perfect round = 10 consecutive correct answers
    if streak >= 10:
        perfect_round_count += 1
        _reset_perfect_round_tracking()  # Reset after achieving it

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
        "total": total_roadblocks,
        "difficulty": difficulty
    }

func save_game() -> void:
    var save_data := {
        "xp": xp,
        "coins": coins,
        "level": level,
        "streak": streak,
        "total_roadblocks": total_roadblocks,
        "correct_answers": correct_answers,
        "wrong_answers": wrong_answers,
        "achievements": achievements
    }
    SaveManager.save_game(save_data)
    emit_signal("game_saved")

func load_game() -> void:
    var save_data := SaveManager.load_game()
    _apply_save_data(save_data)
    emit_signal("game_loaded")

func _update_signals() -> void:
    emit_signal("xp_changed", 0)  # Just to update UI
    emit_signal("coins_changed", 0)
    emit_signal("level_changed", level)
