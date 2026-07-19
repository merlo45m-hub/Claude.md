import { Command, FuzzyMatch } from './types';

/**
 * Fuzzy search implementation that matches characters in order
 * and scores based on consecutive matches and match position.
 */
export function fuzzyMatch(query: string, text: string): { score: number; matches: number[] } | null {
  if (!query) return { score: 1, matches: [] };

  const queryLower = query.toLowerCase();
  const textLower = text.toLowerCase();

  const matches: number[] = [];
  let queryIndex = 0;
  let score = 0;
  let consecutiveBonus = 0;
  let lastMatchIndex = -1;

  for (let i = 0; i < textLower.length && queryIndex < queryLower.length; i++) {
    if (textLower[i] === queryLower[queryIndex]) {
      matches.push(i);

      // Bonus for consecutive matches
      if (lastMatchIndex === i - 1) {
        consecutiveBonus += 5;
      } else {
        consecutiveBonus = 0;
      }

      // Bonus for matching at word boundaries
      const isWordBoundary = i === 0 || textLower[i - 1] === ' ' || textLower[i - 1] === '-';
      const wordBoundaryBonus = isWordBoundary ? 10 : 0;

      // Bonus for early matches
      const positionBonus = Math.max(0, 10 - i);

      score += 1 + consecutiveBonus + wordBoundaryBonus + positionBonus;
      lastMatchIndex = i;
      queryIndex++;
    }
  }

  // Return null if not all query characters were matched
  if (queryIndex < queryLower.length) {
    return null;
  }

  // Normalize score by query length to favor shorter queries that match well
  return {
    score: score / query.length,
    matches,
  };
}

/**
 * Search commands using fuzzy matching on label and keywords.
 */
export function searchCommands(query: string, commands: Command[]): FuzzyMatch[] {
  if (!query.trim()) {
    return commands.map((command) => ({
      command,
      score: 0,
      matches: [],
    }));
  }

  const results: FuzzyMatch[] = [];

  for (const command of commands) {
    // Check if command is enabled
    if (command.isEnabled && !command.isEnabled()) {
      continue;
    }

    // Try to match on label
    const labelMatch = fuzzyMatch(query, command.label);

    // Try to match on keywords
    let keywordScore = 0;
    for (const keyword of command.keywords) {
      const kwMatch = fuzzyMatch(query, keyword);
      if (kwMatch && kwMatch.score > keywordScore) {
        keywordScore = kwMatch.score * 0.8; // Keyword matches worth 80% of label matches
      }
    }

    // Use the better score
    if (labelMatch || keywordScore > 0) {
      const score = Math.max(labelMatch?.score ?? 0, keywordScore);
      results.push({
        command,
        score,
        matches: labelMatch?.matches ?? [],
      });
    }
  }

  // Sort by score descending
  results.sort((a, b) => b.score - a.score);

  return results;
}

/**
 * Highlight matched characters in text.
 */
export function highlightMatches(text: string, matches: number[]): { text: string; highlighted: boolean }[] {
  if (matches.length === 0) {
    return [{ text, highlighted: false }];
  }

  const result: { text: string; highlighted: boolean }[] = [];
  let lastIndex = 0;

  for (const matchIndex of matches) {
    // Add non-highlighted text before match
    if (matchIndex > lastIndex) {
      result.push({
        text: text.slice(lastIndex, matchIndex),
        highlighted: false,
      });
    }

    // Add highlighted character
    result.push({
      text: text[matchIndex],
      highlighted: true,
    });

    lastIndex = matchIndex + 1;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    result.push({
      text: text.slice(lastIndex),
      highlighted: false,
    });
  }

  return result;
}
