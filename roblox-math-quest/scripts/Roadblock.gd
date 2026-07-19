extends Control

# Signals
signal answer_correct
signal answer_wrong
signal retry_exhausted  # when retries are used up and hint is shown

# Exported variables for tuning
@export var max_retries := 2
@export var shake_duration := 0.3
@export var shake_magnitude := 10

# Internal state
var correct_answer := 0
var retries_left := 0
var hint_shown := false

# NodePath

func set_problem(question_text: String, answer: int, options: Array) -> void:
    $ProblemLabel.text = question_text
    correct_answer = answer
    retries_left = max_retries
    hint_shown = false
    # Set the answer buttons
    $AnswersContainer/Answer1.text = str(options[0])
    $AnswersContainer/Answer2.text = str(options[1])
    $AnswersContainer/Answer3.text = str(options[2])
    $AnswersContainer/Answer4.text = str(options[3])

func _on_Answer1_pressed() -> void:
    _check_answer($AnswersContainer/Answer1.text.to_int())

func _on_Answer2_pressed() -> void:
    _check_answer($AnswersContainer/Answer2.text.to_int())

func _on_Answer3_pressed() -> void:
    _check_answer($AnswersContainer/Answer3.text.to_int())

func _on_Answer4_pressed() -> void:
    _check_answer($AnswersContainer/Answer4.text.to_int())

func _check_answer(answer: int) -> void:
    if answer == correct_answer:
        answer_correct.emit()
        play_correct_effect()
    else:
        retries_left -= 1
        if retries_left > 0:
            # Wrong but retries left: shake and allow another try
            play_wrong_effect()
        else:
            # No retries left: show hint and signal retry exhausted
            play_wrong_effect()
            show_hint()
            retry_exhausted.emit()

func play_correct_effect() -> void:
    # Play break animation
    $AnimationPlayer.play("break")
    # Play SFX (we'll assume an AudioStreamPlayer is set up elsewhere, but for now just a placeholder)
    # You can add an AudioStreamPlayer node and call play() on it.
    # For haptic feedback, we'll call it from Main via signal, but we can also do it here if we have access to Input.
    # However, to keep the roadblock reusable, we'll leave haptics to the main scene.
    # We'll just emit a signal for correct and let Main handle SFX and haptics.
    # Actually, let's keep the roadblock self-contained for effects and have Main handle game logic.
    # We'll change: roadblock emits signals for correct/wrong, and Main handles the game state (XP, coins, etc.)
    # But for the effects (animation, shake, hint) we keep in roadblock.
    # So we'll play the animation and optionally a sound if we have an AudioStreamPlayer.
    # Let's assume we have an AudioStreamPlayer for correct and wrong.
    # We'll add them as optional exported variables.

func play_wrong_effect() -> void:
    # Shake the entire roadblock (or just the container)
    var tween := create_tween()
    tween.tween_property($Container, "position:offset", Vector2(-shake_magnitude, 0), shake_duration/4)
    tween.tween_property($Container, "position:offset", Vector2(shake_magnitude, 0), shake_duration/4)
    tween.tween_property($Container, "position:offset", Vector2(-shake_magnitude, 0), shake_duration/4)
    tween.tween_property($Container, "position:offset", Vector2(shake_magnitude, 0), shake_duration/4)
    tween.tween_property($Container, "position:offset", Vector2(0, 0), shake_duration/4)
    # Again, we assume Main will handle SFX and haptics for wrong answer.

func show_hint() -> void:
    # For now, just show the correct answer as a hint
    $ProblemLabel.text = "Answer: %s" % str(correct_answer)
    hint_shown = true
    # Disable further input
    $AnswersContainer/Answer1.disabled = true
    $AnswersContainer/Answer2.disabled = true
    $AnswersContainer/Answer3.disabled = true
    $AnswersContainer/Answer4.disabled = true

# We'll also add a reset function for when we want to reuse the roadblock (though we are instancing new ones)
func _ready() -> void:
    pass