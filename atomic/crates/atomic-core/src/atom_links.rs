//! Parsing helpers for Obsidian-style atom links in markdown.
//!
//! This module intentionally only resolves UUID-shaped targets today. Other
//! targets are preserved as unresolved raw text so slug/title/alias resolution
//! can be added later without changing the parser contract.

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ParsedAtomLink {
    pub raw_target: String,
    pub label: Option<String>,
    pub start_offset: usize,
    pub end_offset: usize,
}

pub(crate) fn is_uuid_target(value: &str) -> bool {
    let value = value.trim();
    value.len() == 36
        && value.as_bytes().get(8) == Some(&b'-')
        && value.as_bytes().get(13) == Some(&b'-')
        && value.as_bytes().get(18) == Some(&b'-')
        && value.as_bytes().get(23) == Some(&b'-')
        && uuid::Uuid::parse_str(value).is_ok()
}

pub(crate) fn extract_atom_link_tokens(markdown: &str) -> Vec<ParsedAtomLink> {
    let mut links = Vec::new();
    let mut line_start = 0;
    let mut in_fenced_code = false;

    for line_with_newline in markdown.split_inclusive('\n') {
        let line = line_with_newline.trim_end_matches('\n');
        let trimmed = line.trim_start();
        if trimmed.starts_with("```") || trimmed.starts_with("~~~") {
            in_fenced_code = !in_fenced_code;
            line_start += line_with_newline.len();
            continue;
        }

        if !in_fenced_code {
            extract_links_from_line(line, line_start, &mut links);
        }

        line_start += line_with_newline.len();
    }

    if line_start < markdown.len() {
        let line = &markdown[line_start..];
        if !in_fenced_code {
            extract_links_from_line(line, line_start, &mut links);
        }
    }

    links
}

fn extract_links_from_line(line: &str, line_start: usize, links: &mut Vec<ParsedAtomLink>) {
    let bytes = line.as_bytes();
    let mut i = 0;
    let mut inline_code_ticks = 0usize;

    while i < bytes.len() {
        if bytes[i] == b'`' {
            let tick_count = count_repeated(bytes, i, b'`');
            if inline_code_ticks == 0 {
                inline_code_ticks = tick_count;
            } else if inline_code_ticks == tick_count {
                inline_code_ticks = 0;
            }
            i += tick_count;
            continue;
        }

        if inline_code_ticks == 0 && bytes[i] == b'[' && bytes.get(i + 1) == Some(&b'[') {
            if let Some(close) = find_wiki_link_close(bytes, i + 2) {
                let inner = &line[i + 2..close];
                if let Some((raw_target, label)) = parse_inner_link(inner) {
                    links.push(ParsedAtomLink {
                        raw_target,
                        label,
                        start_offset: line_start + i,
                        end_offset: line_start + close + 2,
                    });
                }
                i = close + 2;
                continue;
            }
        }

        i += 1;
    }
}

fn count_repeated(bytes: &[u8], start: usize, needle: u8) -> usize {
    let mut count = 0;
    while bytes.get(start + count) == Some(&needle) {
        count += 1;
    }
    count
}

fn find_wiki_link_close(bytes: &[u8], mut start: usize) -> Option<usize> {
    while start + 1 < bytes.len() {
        if bytes[start] == b']' && bytes[start + 1] == b']' {
            return Some(start);
        }
        start += 1;
    }
    None
}

fn parse_inner_link(inner: &str) -> Option<(String, Option<String>)> {
    let inner = inner.trim();
    if inner.is_empty() {
        return None;
    }

    let (target, label) = match inner.split_once('|') {
        Some((target, label)) => (target.trim(), Some(label.trim())),
        None => (inner, None),
    };

    if target.is_empty() {
        return None;
    }

    Some((
        target.to_string(),
        label.filter(|s| !s.is_empty()).map(ToString::to_string),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_id_links_and_labels() {
        let id = "550e8400-e29b-41d4-a716-446655440000";
        let content = format!("before [[{}|Readable]] after [[{}]]", id, id);
        let links = extract_atom_link_tokens(&content);

        assert_eq!(links.len(), 2);
        assert_eq!(links[0].raw_target, id);
        assert_eq!(links[0].label.as_deref(), Some("Readable"));
        assert_eq!(links[1].raw_target, id);
        assert_eq!(links[1].label, None);
        assert!(is_uuid_target(&links[0].raw_target));
    }

    #[test]
    fn preserves_non_uuid_targets_as_unresolved_candidates() {
        let links = extract_atom_link_tokens("[[future-slug|Future]] and [[Loose Title]]");
        assert_eq!(links.len(), 2);
        assert_eq!(links[0].raw_target, "future-slug");
        assert_eq!(links[1].raw_target, "Loose Title");
        assert!(!is_uuid_target(&links[0].raw_target));
    }

    #[test]
    fn ignores_links_inside_code() {
        let content = "`[[inline]]`\n\n```\n[[fenced]]\n```\n\n[[real]]";
        let links = extract_atom_link_tokens(content);
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].raw_target, "real");
    }
}
