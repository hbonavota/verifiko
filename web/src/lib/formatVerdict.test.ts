import { describe, expect, it } from "vitest";

import { formatRiskLevel, formatVerdict } from "./formatVerdict";

describe("formatVerdict", () => {
  it("maps backend verdicts to the four user-facing labels in both languages", () => {
    expect(formatVerdict("TRUSTED")).toBe("Safe");
    expect(formatVerdict("NEEDS_REVIEW")).toBe("Suspicious");
    expect(formatVerdict("likely_malicious", "es")).toBe("Malicioso");
    expect(formatVerdict("CONFIRMED_MALICIOUS")).toBe("Malicious");
    expect(formatVerdict("caution", "es")).toBe("Precaución");
  });

  it("normalizes underscores, extra whitespace and case before matching", () => {
    expect(formatVerdict("  needs__review ")).toBe("Suspicious");
    expect(formatVerdict("Likely   Malicious", "es")).toBe("Malicioso");
  });

  it("title-cases verdicts it does not know instead of dropping them", () => {
    expect(formatVerdict("NEW_VERDICT_KIND")).toBe("New Verdict Kind");
  });
});

describe("formatRiskLevel", () => {
  it("localizes known levels and passes unknown ones through upper-cased", () => {
    expect(formatRiskLevel(" critical ")).toBe("Critical");
    expect(formatRiskLevel("MEDIUM", "es")).toBe("Medio");
    expect(formatRiskLevel("extreme")).toBe("EXTREME");
  });
});
