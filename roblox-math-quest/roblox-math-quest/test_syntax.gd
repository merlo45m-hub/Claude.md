# Test script to verify GDScript syntax without GUI
# This can be run with: godot --headless -s test_syntax.gd
extends Node

func _ready() -> void:
    print("Testing GDScript syntax...")
    
    # Test GameManager basics
    var gm = Node.new()
    gm.set_script(load("res://Autoload/GameManager.gd"))
    gm._ready()
    
    # Test adding points
    gm.add_correct_answer()
    print("XP after correct answer: %d" % gm.xp)
    print("Coins after correct answer: %d" % gm.coins)
    
    # Test level up calculation
    var xp_needed = 100  # XP_PER_LEVEL_BASE
    while gm.xp < xp_needed:
        gm.add_correct_answer()
    print("Level after earning enough XP: %d" % gm.level)
    
    print("Syntax test completed successfully!")
