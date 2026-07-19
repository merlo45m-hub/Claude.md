use std::fs;
use std::path::PathBuf;

fn main() {
    tauri_build::build();

    // Copy resources to target directory for development
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let target_dir = manifest_dir.join("target");
    let profile = std::env::var("PROFILE").unwrap_or_else(|_| "debug".to_string());
    let resources_target = target_dir.join(&profile).join("resources");
    let resources_source = manifest_dir.join("resources");

    // Create target resources directory
    if let Err(e) = fs::create_dir_all(&resources_target) {
        println!("cargo:warning=Failed to create resources directory: {}", e);
        return;
    }

    // Copy all resource files
    if let Ok(entries) = fs::read_dir(&resources_source) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                let file_name = path.file_name().unwrap();
                let dest = resources_target.join(file_name);
                if let Err(e) = fs::copy(&path, &dest) {
                    println!("cargo:warning=Failed to copy {}: {}", path.display(), e);
                }
            }
        }
    }

    // Re-run if resources change
    println!("cargo:rerun-if-changed=resources");
}
