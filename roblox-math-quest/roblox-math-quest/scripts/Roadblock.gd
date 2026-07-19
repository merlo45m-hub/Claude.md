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

# Node paths (will be set in _ready)
var problem_label: Label
var answers_container: GridContainer
var answer_buttons: Array
var animation_player: AnimationPlayer

func _ready() -> void:
    problem_label = $ProblemLabel
    answers_container = $AnswersContainer
    answer_buttons = [$Answer1, $Answer2, $Answer3, $Answer4]
    animation_player = $AnimationPlayer
    
    # Connect button signals
    for button in answer_buttons:
        button.pressed.connect(_on_button_pressed)
    
    # Setup animations
    _setup_animations()

func set_problem(question_text: String, answer: int, options: Array) -> void:
    problem_label.text = question_text
    correct_answer = answer
    retries_left = max_retries
    hint_shown = false
    
    # Shuffle options and assign to buttons
    options.shuffle()
    for i in range(min(answer_buttons.size(), options.size())):
        answer_buttons[i].text = str(options[i])
        answer_buttons[i].disabled = false
        answer_buttons[i].modulate = Color(1, 1, 1, 1)  # reset color

func _setup_animations() -> void:
    # Correct answer animation (scale up + green flash)
    animation_player.create_animation("correct", 0.5)
    animation_player.animation_track_insert_key("correct", "scale", 0.0, Vector2(1, 1))
    animation_player.animation_track_insert_key("correct", "scale", 0.1, Vector2(1.2, 1.2))
    animation_player.animation_track_insert_key("correct", "scale", 0.2, Vector2(1, 1))
    animation_player.animation_track_insert_method_call("correct", 0.0, Callable(self, "_flash_correct").bind())
    animation_player.animation_track_insert_method_call("correct", 0.2, Callable(self, "_reset_button_colors").bind())
    
    # Wrong answer animation (shake + red flash)
    animation_player.create_animation("wrong", 0.5)
    animation_player.animation_track_insert_key("wrong", "offset", 0.0, Vector2(0, 0))
    for i in range(6):
        var offset_x = sin(i * PI) * shake_magnitude
        var offset_y = cos(i * PI * 0.5) * shake_magnitude * 0.5
        animation_player.animation_track_insert_key("wrong", "offset", (i + 1) * 0.1, Vector2(offset_x, offset_y))
    animation_player.animation_track_insert_key("wrong", "offset", 0.6, Vector2(0, 0))
    animation_player.animation_track_insert_method_call("wrong", 0.0, Callable(self, "_flash_wrong").bind())
    animation_player.animation_track_insert_method_call("wrong", 0.5, Callable(self, "_reset_button_colors").bind())

func _on_button_pressed(button: Button) -> void:
    var answer := int(button.text)
    if answer == correct_answer:
        _on_correct()
    else:
        _on_wrong()

func _on_correct() -> void:
    # Disable buttons
    for b in answer_buttons:
        b.disabled = true
    # Play correct animation
    animation_player.play("correct")
    # Emit signal after animation
    var timer := Timer.new()
    timer.wait_time = 0.5
    timer.one_shot = true
    add_child(timer)
    timer.timeout.connect(() => {
        answer_correct.emit()
        queue_free()
    })
    timer.start()

func _on_wrong() -> void:
    retries_left -= 1
    if retries_left > 0:
        # Wrong but has retries left - shake and flash red
        animation_player.play("wrong")
        # Disable this button temporarily
        (button as Button).disabled = true
        var timer := Timer.new()
        timer.wait_time = 0.5
        timer.one_shot = true
        add_child(timer)
        timer.timeout.connect(() => {
            (button as Button).disabled = false
        })
        timer.start()
    else:
        # Out of retries - show hint
        _show_hint()

func _show_hint() -> void:
    hint_shown = true
    # Show correct answer in green
    for button in answer_buttons:
        if int(button.text) == correct_answer:
            button.modulate = Color(0, 1, 0, 1)
            break
    # Disable all buttons
    for b in answer_buttons:
        b.disabled = true
    # Emit signal that retries are exhausted
    retry_exhausted.emit()

func _flash_correct() -> void:
    # Flash all buttons green briefly
    for button in answer_buttons:
        button.modulate = Color(0, 1, 0, 1)

def _flash_wrong(self) -> None:
    # Flash all buttons red briefly
    for button in answer_buttons:
        button.modulate = Color(1, 0, 0, 1)

def _reset_button_colors(self) -> None:
    # Reset button colors to white
    for button in answer_buttons:
        button.modulate = Color(1, 1, 1, 1)
