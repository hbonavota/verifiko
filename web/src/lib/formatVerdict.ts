export function formatVerdict(verdict: string) {
  return verdict.replace(/_/g, " ").replace(/\s+/g, " ").trim();
}
