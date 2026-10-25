import { describe, expect, it } from "vitest";

import { degradedCoverageAreas, resultNote, type CoverageNoteCopy } from "./coverageNote";

const scoreGuide = {
  highDanger: "high danger",
  strongCaution: "strong caution",
  caution: "caution",
  safe: "safe",
};

const coverageNote: CoverageNoteCopy = {
  body: "Some checks could not be completed: {areas}.",
  areas: {
    domain: "domain age",
    redirects: "redirects",
    reputation: "reputation",
    infrastructure: "infrastructure",
    security: "TLS",
    content: "page content",
  },
};

describe("degradedCoverageAreas", () => {
  it("detects areas from English and Spanish warnings alike, without duplicates", () => {
    expect(
      degradedCoverageAreas([
        "Reputation providers were unavailable.",
        "No se pudo consultar la reputación del dominio.",
        "El registro del dominio no está disponible.",
        "TLS handshake failed.",
      ]),
    ).toEqual(["reputation", "domain", "security"]);
  });

  it("ignores empty and non-degrading (user-agent) warnings", () => {
    expect(
      degradedCoverageAreas(["", "Content differed by user agent; analysis continued."]),
    ).toEqual([]);
  });
});

describe("resultNote", () => {
  it("prefers the coverage caveat over the score interpretation", () => {
    expect(
      resultNote({
        score: 95,
        warnings: ["Redirect chain could not be followed.", "HTML could not be fetched."],
        scoreGuide,
        coverageNote,
      }),
    ).toBe("Some checks could not be completed: redirects, page content.");
  });

  it("falls back to the score bands, with inclusive upper bounds at 40/60/80", () => {
    const note = (score: number) => resultNote({ score, warnings: [], scoreGuide, coverageNote });

    expect(note(0)).toBe("high danger");
    expect(note(40)).toBe("high danger");
    expect(note(41)).toBe("strong caution");
    expect(note(60)).toBe("strong caution");
    expect(note(80)).toBe("caution");
    expect(note(81)).toBe("safe");
  });
});
