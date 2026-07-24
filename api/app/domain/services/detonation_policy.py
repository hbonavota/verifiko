from dataclasses import dataclass

from app.domain.enums.risk_level import RiskLevel


@dataclass(frozen=True, slots=True)
class DetonationPolicy:
    """Decides whether a URL is worth detonating in a headless browser.

    Detonation is slow and costs money, so it is reserved for cases where the
    dynamic evidence can actually change the outcome:

    - The URL-only analysis is already decisively malicious (HIGH/CRITICAL) — the
      fast-path orchestrator has decided; detonation would not change the verdict,
      so it is skipped on the automatic path.
    - The URL-only analysis is in the suspicious middle (LOW/MEDIUM) — this is
      exactly where actually loading the page adds the most information, so it is
      detonated.
    - Clearly benign (SAFE) URLs are not detonated automatically.

    When the caller explicitly requests a deep scan, we honour it and detonate
    regardless of the preliminary level (they opted in and pay for it).
    """

    def should_detonate(
        self, url_only_risk_level: RiskLevel, *, deep_scan_requested: bool = False
    ) -> bool:
        if deep_scan_requested:
            return True
        return url_only_risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}
