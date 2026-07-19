use serde::{Deserialize, Serialize};

/// A single markdown edit operation for an atom.
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
pub struct AtomEditOperation {
    pub operation: String,
    #[serde(default)]
    pub old_text: Option<String>,
    #[serde(default)]
    pub new_text: Option<String>,
    #[serde(default)]
    pub anchor_text: Option<String>,
    #[serde(default)]
    pub text: Option<String>,
    #[serde(default)]
    pub content: Option<String>,
}

fn exact_match_range(
    content: &str,
    needle: &str,
    edit_index: usize,
) -> Result<(usize, usize), String> {
    if needle.is_empty() {
        return Err(format!("Edit {} has empty anchor text", edit_index + 1));
    }

    let mut matches = content.match_indices(needle);
    let Some((start, matched)) = matches.next() else {
        return Err(format!(
            "Edit {} anchor text was not found exactly once",
            edit_index + 1
        ));
    };
    if matches.next().is_some() {
        return Err(format!(
            "Edit {} anchor text matched more than once; use a more specific anchor",
            edit_index + 1
        ));
    }

    Ok((start, start + matched.len()))
}

pub fn apply_atom_edits(content: &str, edits: &[AtomEditOperation]) -> Result<String, String> {
    if edits.is_empty() {
        return Err("At least one edit is required".to_string());
    }

    let mut updated = content.to_string();
    for (index, edit) in edits.iter().enumerate() {
        match edit.operation.as_str() {
            "replace" => {
                let old_text = edit
                    .old_text
                    .as_deref()
                    .ok_or_else(|| format!("Edit {} is missing old_text", index + 1))?;
                let new_text = edit
                    .new_text
                    .as_deref()
                    .ok_or_else(|| format!("Edit {} is missing new_text", index + 1))?;
                let (start, end) = exact_match_range(&updated, old_text, index)?;
                updated.replace_range(start..end, new_text);
            }
            "insert_after" => {
                let anchor_text = edit
                    .anchor_text
                    .as_deref()
                    .ok_or_else(|| format!("Edit {} is missing anchor_text", index + 1))?;
                let text = edit
                    .text
                    .as_deref()
                    .ok_or_else(|| format!("Edit {} is missing text", index + 1))?;
                let (_, end) = exact_match_range(&updated, anchor_text, index)?;
                updated.insert_str(end, text);
            }
            "append" => {
                let text = edit
                    .text
                    .as_deref()
                    .ok_or_else(|| format!("Edit {} is missing text", index + 1))?;
                updated.push_str(text);
            }
            "replace_all" => {
                let content = edit
                    .content
                    .as_deref()
                    .ok_or_else(|| format!("Edit {} is missing content", index + 1))?;
                updated = content.to_string();
            }
            operation => {
                return Err(format!(
                    "Edit {} has unsupported operation '{}'",
                    index + 1,
                    operation
                ));
            }
        }
    }

    Ok(updated)
}

#[cfg(test)]
mod tests {
    use super::{apply_atom_edits, AtomEditOperation};

    #[test]
    fn apply_atom_edits_supports_replace_insert_and_append() {
        let edits = vec![
            AtomEditOperation {
                operation: "replace".to_string(),
                old_text: Some("old item".to_string()),
                new_text: Some("new item".to_string()),
                anchor_text: None,
                text: None,
                content: None,
            },
            AtomEditOperation {
                operation: "insert_after".to_string(),
                old_text: None,
                new_text: None,
                anchor_text: Some("## Tasks\n".to_string()),
                text: Some("\nIntro line\n".to_string()),
                content: None,
            },
            AtomEditOperation {
                operation: "append".to_string(),
                old_text: None,
                new_text: None,
                anchor_text: None,
                text: Some("\n\nDone.".to_string()),
                content: None,
            },
        ];

        let updated = apply_atom_edits("# Note\n\n## Tasks\n- old item", &edits).unwrap();

        assert_eq!(
            updated,
            "# Note\n\n## Tasks\n\nIntro line\n- new item\n\nDone."
        );
    }

    #[test]
    fn apply_atom_edits_supports_replace_all() {
        let edits = vec![AtomEditOperation {
            operation: "replace_all".to_string(),
            old_text: None,
            new_text: None,
            anchor_text: None,
            text: None,
            content: Some("# Replacement\n\nFull body.".to_string()),
        }];

        let updated = apply_atom_edits("# Original\n\nOld body.", &edits).unwrap();

        assert_eq!(updated, "# Replacement\n\nFull body.");
    }

    #[test]
    fn apply_atom_edits_rejects_missing_anchor() {
        let edits = vec![AtomEditOperation {
            operation: "replace".to_string(),
            old_text: Some("missing".to_string()),
            new_text: Some("replacement".to_string()),
            anchor_text: None,
            text: None,
            content: None,
        }];

        let error = apply_atom_edits("content", &edits).unwrap_err();

        assert!(error.contains("not found"));
    }

    #[test]
    fn apply_atom_edits_rejects_ambiguous_anchor() {
        let edits = vec![AtomEditOperation {
            operation: "insert_after".to_string(),
            old_text: None,
            new_text: None,
            anchor_text: Some("same".to_string()),
            text: Some("!".to_string()),
            content: None,
        }];

        let error = apply_atom_edits("same and same", &edits).unwrap_err();

        assert!(error.contains("matched more than once"));
    }
}
