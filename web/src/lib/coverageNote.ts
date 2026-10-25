// Derives a human-friendly, localized "some checks couldn't be completed" note
// from the backend's structured coverage warnings — so end users never see the
// raw penalty-math summary, and the note is always in their language.

export type CoverageArea =
  "domain" | "redirects" | "reputation" | "infrastructure" | "security" | "content";

// Each area is detected by substrings that appear in the localized warning text
// in BOTH English and Spanish, so it works regardless of the response language.
const AREA_PATTERNS: ReadonlyArray<readonly [CoverageArea, RegExp]> = [
  ["domain", /domain registration|registro del dominio/i],
  ["redirects", /redirect|redirecc/i],
  ["reputation", /reputation|reputaci/i],
  ["infrastructure", /infrastructure|infraestructura/i],
  ["security", /\bTLS\b/i],
  [
    "content",
    /html|content|contenido|dynamic|dinámic|detonaci|resolved destination|destino resuelto/i,
  ],
];

// Non-degrading warnings: the analysis explicitly continued despite them, so
// they must not be surfaced as a coverage gap.
const NON_DEGRADING = /user-agent|user agent/i;

export function degradedCoverageAreas(warnings: readonly string[]): CoverageArea[] {
  const areas = new Set<CoverageArea>();
  for (const warning of warnings) {
    if (!warning || NON_DEGRADING.test(warning)) {
      continue;
    }
    for (const [area, pattern] of AREA_PATTERNS) {
      if (pattern.test(warning)) {
        areas.add(area);
      }
    }
  }
  return [...areas];
}

export interface ScoreInterpretationCopy {
  highDanger: string;
  strongCaution: string;
  caution: string;
  safe: string;
}

export interface CoverageNoteCopy {
  body: string; // must contain the "{areas}" placeholder
  areas: Record<CoverageArea, string>;
}

export function scoreInterpretationCopy(score: number, copy: ScoreInterpretationCopy): string {
  if (score <= 40) {
    return copy.highDanger;
  }
  if (score <= 60) {
    return copy.strongCaution;
  }
  if (score <= 80) {
    return copy.caution;
  }
  return copy.safe;
}

export function buildCoverageNote(
  warnings: readonly string[],
  copy: CoverageNoteCopy,
): string | null {
  const areas = degradedCoverageAreas(warnings);
  if (areas.length === 0) {
    return null;
  }
  const labels = areas.map((area) => copy.areas[area]);
  return copy.body.replace("{areas}", labels.join(", "));
}

// The user-facing result note: a friendly coverage caveat when checks were
// skipped, otherwise the localized score interpretation. Never the raw summary.
export function resultNote(params: {
  score: number;
  warnings: readonly string[];
  scoreGuide: ScoreInterpretationCopy;
  coverageNote: CoverageNoteCopy;
}): string {
  return (
    buildCoverageNote(params.warnings, params.coverageNote) ??
    scoreInterpretationCopy(params.score, params.scoreGuide)
  );
}
