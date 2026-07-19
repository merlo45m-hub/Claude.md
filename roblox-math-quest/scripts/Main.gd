extends Node2D

# Exported variables for tuning
@export var problem_min_number := 1
@export var problem_max_number := 20
@export var problem_operation := "+"  # could be "-", "*", "/" later
@export var roadblock_scene := preload("res://Roadblock.tscn")
@export var minigame_scenes := [
    preload("res://MiniGames/TapNumbers.tscn"),
    preload("res://MiniGames/MemoryMatch.tscn"),
    preload("res://MiniGames/NumberSlice.tscn"),
    preload("res://MiniGames/PatternFill.tscn")
]

# Internal state
var roadblocks_since_last_minigame := 0
var current_roadblock := nil

func _ready() -> void:
    # Connect to GameManager signals
    GameManager.xp_changed.connect(_on_xp_changed)
    GameManager.coins_changed.connect(_on_coins_changed)
    GameManager.level_changed.connect(_on_level_changed)
    GameManager.achievement_unlocked.connect(_on_achievement_unlocked)
    
    # Load saved data
    SaveManager.load_game()
    
    # Update UI labels
    _update_ui_labels()
    
    # Spawn first roadblock
    spawn_roadblock()

func spawn_roadblock() -> void:
    if current_roadblock:
        current_roadblock.queue_free()
    current_roadblock = roadblock_scene.instantiate()
    add_child(current_roadblock)
    # Configure roadblock with a new problem
    var problem := _generate_problem()
    current_roadblock.set_problem(problem.question, problem.answer, problem.options)
    # Connect signals from roadblock
    current_roadblock.answer_correct.connect(_on_roadblock_correct)
    current_roadblock.answer_wrong.connect(_on_roadblock_wrong)

func _generate_problem() -> Dictionary:
    var a := randi() % (problem_max_number - problem_min_number + 1) + problem_min_number
    var b := randi() % (problem_max_number - problem_min_number + 1) + problem_min_number
    var correct_answer := 0
    match problem_operation:
        "+":
            correct_answer = a + b
        "-":
            # ensure non-negative
            if a < b:
                var tmp = a
                a = b
                b = tmp
            correct_answer = a - b
        "*":
            correct_answer = a * b
        "/":
            # ensure divisible
            b = max(1, b)
            a = b * ((randi() % 10) + 1)  # make a multiple of b
            correct_answer = a / b
    # Generate 3 wrong answers
    var wrong_answers := []
    var i := 0
    while i < 3:
        var wrong := correct_answer + randi() % 10 - 5
        if wrong == correct_answer or wrong in wrong_answers:
            continue
        wrong_answers.append(wrong)
        i += 1
    var options := [correct_answer] + wrong_answers
    options.shuffle()
    var question := str(a) + " " + problem_operation + " " + str(b) + " = ?"
    return {
        "question": question,
        "answer": correct_answer,
        "options": options
    }

func _on_roadblock_correct() -> void:
    # Correct answer: give XP/coins, play effect, then remove roadblock and maybe spawn minigame
    GameManager.add_xp(GameManager.XP_PER_CORRECT)
    GameManager.add_coins(GameManager.COINS_PER_CORRECT)
    GameManager.increment_streak()
    # Play correct SFX and animation via roadblock
    current_roadblock.play_correct_effect()
    # Wait a bit then remove roadblock
    var timer := Timer.new()
    timer.wait_time = 0.8
    timer.one_shot = true
    add_child(timer)
    timer.timeout.connect(func():
        current_roadblock.queue_free()
        current_roadblock = nil
        roadblocks_since_last_minigame += 1
        if roadblocks_since_last_minigame >= GameManager.MINIGAME_INTERVAL:
            spawn_minigame()
        else:
            spawn_roadblock()
    )
    timer.start()

func _on_roadblock_wrong() -> void:
    # Wrong answer: play wrong effect, allow retries
    GameManager.reset_streak()
    current_roadblock.play_wrong_effect()
    # Could implement retry logic here; for simplicity, we just let roadblock handle retries internally
    # Assume roadblock will call back after retries exhausted or after hint shown
    # For now, we'll just wait a bit and then respawn same problem? Let's keep simple:
    # After wrong effect, we allow another attempt (roadblock internal handles retries)
    pass

func spawn_minigame() -> void:
    if current_roadblock:
        current_roadblock.queue_free()
        current_roadblock = nil
    var minigame_scene := minigame_scenes[randi() % minigame_scenes.size()]
    var minigame := minigame_scene.instantiate()
    add_child(minigame)
    minigame.game_completed.connect(_on_minigame_completed)

func _on_minigame_completed() -> void:
    # Mini-game finished, give bonus XP/coins
    GameManager.add_xp(20)
    GameManager.add_coins(10)
    get_node("./").remove_child(get_node("./").get_children()[-1])  # remove the minigame node (assuming it's the last child)
    roadblocks_since_last_minigame = 0
    spawn_roadblock()

func _on_xp_changed(amount) -> void:
    _update_ui_labels()
    # Check for level up
    if GameManager.current_xp >= GameManager.xp_for_next_level:
        GameManager.level_up()

func _on_coins_changed(amount) -> void:
    _update_ui_labels()

func _on_level_changed(new_level) -> void:
    _update_ui_labels()
    # Show level up overlay
    var overlay := get_node("./LevelUpOverlay")
    overlay.visible = true
    var tween := create_tween()
    tween.tween_property(overlay, "modulate:a", 1.0, 0.3)
    tween.tween_interval(0.5)
    tween.tween_property(overlay, "modulate:a", 0.0, 0.3)
    tween.finished.connect(func():
        overlay.visible = false
    )

func _on_achievement_unlocked(achievement_id) -> void:
    # TODO: show toast or notification
    print("Achievement unlocked: %s" % achievement_id)

func _update_ui_labels() -> void:
    get_node("./UI/LevelLabel").text = "Level: %d" % GameManager.current_level
    get_node("./UI/CoinsLabel").text = "Coins: %d" % GameManager.current_coins
    get_node("./UI/StreakLabel").text = "Streak: %d" % GameManager.current_streak
    var xp_percent := 0.0
    if GameManager.xp_for_next_level > 0:
        xp_percent = float(GameManager.current_xp) / float(GameManager.xp_for_next_level)
    get_node("./UI/XPBar").value = xp_percent * 100
