export function formatVerdict(verdict: string) {
  const normalizedVerdict = verdict.replace(/_/g, " ").replace(/\s+/g, " ").trim().toUpperCase();

  if (normalizedVerdict === "TRUSTED" || normalizedVerdict === "SAFE") {
    return "Safe";
  }

  if (normalizedVerdict === "CAUTION" || normalizedVerdict === "SUSPICIOUS" || normalizedVerdict === "NEEDS REVIEW") {
    return "Suspicious";
  }

  if (normalizedVerdict === "LIKELY MALICIOUS" || normalizedVerdict === "CONFIRMED MALICIOUS") {
    return "Malicious";
  }

  return normalizedVerdict
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
