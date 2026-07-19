use atomic_server::ApiDoc;
use std::{env, fs, path::PathBuf};
use utoipa::OpenApi;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut spec = serde_json::to_value(ApiDoc::openapi())?;

    if let Ok(version) = env::var("ATOMIC_OPENAPI_VERSION") {
        let version = version.trim();
        if !version.is_empty() {
            if let Some(info) = spec.get_mut("info").and_then(|value| value.as_object_mut()) {
                info.insert(
                    "version".to_string(),
                    serde_json::Value::String(version.to_string()),
                );
            }
        }
    }

    let json = serde_json::to_string_pretty(&spec)?;

    if let Some(path) = env::args_os().nth(1) {
        let path = PathBuf::from(path);
        if let Some(parent) = path
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
        {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, format!("{json}\n"))?;
    } else {
        println!("{json}");
    }

    Ok(())
}
