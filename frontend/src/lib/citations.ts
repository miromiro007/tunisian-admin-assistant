export type AnswerSegment =
  | { kind: "text"; value: string }
  | { kind: "citation"; number: number; valid: boolean };

const MARKER_RE = /\[(\d+)\]/g;

/**
 * Splits an answer into plain-text and citation-marker segments.
 * `validNumbers` is the set of citation numbers that should render as
 * clickable chips (source numbers 1..N minus invalid_citations); any other
 * number (explicitly invalid, or out of range entirely) renders as plain
 * text via `valid: false`.
 */
export function parseCitationMarkers(answer: string, validNumbers: Set<number>): AnswerSegment[] {
  const segments: AnswerSegment[] = [];
  let lastIndex = 0;

  for (const match of answer.matchAll(MARKER_RE)) {
    const start = match.index;
    if (start > lastIndex) {
      segments.push({ kind: "text", value: answer.slice(lastIndex, start) });
    }
    const number = Number(match[1]);
    segments.push({ kind: "citation", number, valid: validNumbers.has(number) });
    lastIndex = start + match[0].length;
  }

  if (lastIndex < answer.length) {
    segments.push({ kind: "text", value: answer.slice(lastIndex) });
  }

  return segments;
}

/** Builds the set of chip-eligible numbers from a response's sources + invalid_citations. */
export function buildValidCitationNumbers(sourceNumbers: number[], invalidCitations: number[]): Set<number> {
  const invalid = new Set(invalidCitations);
  return new Set(sourceNumbers.filter((n) => !invalid.has(n)));
}
