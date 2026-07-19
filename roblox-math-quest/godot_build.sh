#!/bin/bash
# godot_build.sh - Helper script for Roblox Math Quest Godot project
# Usage:
#   ./godot_build.sh update <script_name> "<gdscript_code>"
#   ./godot_build.sh add_asset <local_path> <dest_path_in_res>
#   ./godot_build.sh build
#   ./godot_build.sh watch   (optional, requires inotify-tools)

set -euo pipefail

PROJECT_DIR="/root/roblox-math-quest"
ASSETS_DIR="$PROJECT_DIR/assets"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
BUILD_DIR="/root/builds"
GODOT_BIN="godot3"
GODOT_HEADLESS="godot3-server"
EXPORT_PRESET="Android Debug"
EXPORT_PATH="$BUILD_DIR/roblox_math_quest_debug.apk"

# Ensure directories exist
mkdir -p "$ASSETS_DIR" "$SCRIPTS_DIR" "$BUILD_DIR"

# Function to update a GDScript file
update_script() {
    local script_name="$1"
    local script_code="$2"
    local script_path="$SCRIPTS_DIR/$script_name.gd"
    echo "Updating script: $script_path"
    echo "$script_code" > "$script_path"
}

# Function to add an asset
add_asset() {
    local local_path="$1"
    local dest_path="$2"  # e.g., "assets/icon.png" or "scripts/utils.gd"
    local dest="$ASSETS_DIR/$dest_path"
    mkdir -p "$(dirname "$dest")"
    echo "Copying asset: $local_path -> $dest"
    cp "$local_path" "$dest"
}

# Function to build the APK using headless Godot
build_apk() {
    echo "Building APK with Godot headless..."
    # Ensure the export preset exists and the templates are set up
    # We run the editor in headless mode to perform the export
    $GODOT_HEADLESS --path "$PROJECT_DIR" --export-debug "$EXPORT_PRESET" "$EXPORT_PATH"
    echo "APK built at: $EXPORT_PATH"
}

# Function to watch for changes and trigger builds (optional)
watch_and_build() {
    echo "Watching for changes in $ASSETS_DIR and $SCRIPTS_DIR..."
    while inotifywait -r -e modify,create,delete "$ASSETS_DIR" "$SCRIPTS_DIR"; do
        echo "Change detected, building..."
        build_apk
    done
}

# Main command handling
case "${1:-}" in
    update)
        if [[ $# -lt 3 ]]; then
            echo "Usage: $0 update <script_name> \"<gdscript_code>\""
            exit 1
        fi
        update_script "$2" "$3"
        ;;
    add_asset)
        if [[ $# -lt 3 ]]; then
            echo "Usage: $0 add_asset <local_path> <dest_path_in_res>"
            exit 1
        fi
        add_asset "$2" "$3"
        ;;
    build)
        build_apk
        ;;
    watch)
        # Check if inotifywait is available
        if ! command -v inotifywait &> /dev/null; then
            echo "Error: inotify-tools not installed. Install it to use watch mode."
            exit 1
        fi
        watch_and_build
        ;;
    *)
        echo "Usage: $0 {update|add_asset|build|watch}"
        echo "  update <script_name> \"<gdscript_code>\"  Update or create a GDScript script"
        echo "  add_asset <local_path> <dest_path_in_res>  Copy an asset to the project's res:// directory"
        echo "  build                                        Build the APK using headless Godot"
        echo "  watch                                        Watch for changes and trigger builds (requires inotify-tools)"
        exit 1
        ;;
esac