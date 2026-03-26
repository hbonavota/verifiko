import { toneForRiskLevel } from "../../lib/risk";
import type { RiskLevel } from "../../types/verification";

interface ScoreRingProps {
  score?: number;
  label?: string;
  size?: "default" | "hero";
  state?: "ready" | "idle" | "loading";
  valueLabel?: string;
  riskLevel?: RiskLevel;
}

function scoreRingClassName({
  riskLevel,
  size,
  state,
}: Pick<ScoreRingProps, "riskLevel" | "size" | "state">) {
  const classes = ["score-ring"];

  if (size === "hero") {
    classes.push("score-ring--hero");
  }

  if (state === "loading") {
    classes.push("score-ring--neutral", "score-ring--loading");
    return classes.join(" ");
  }

  if (state === "idle" || !riskLevel) {
    classes.push("score-ring--neutral");
    return classes.join(" ");
  }

  const tone = toneForRiskLevel(riskLevel);

  if (tone === "danger") {
    classes.push("score-ring--danger");
  } else if (tone === "warning") {
    classes.push("score-ring--warning");
  } else {
    classes.push("score-ring--success");
  }

  return classes.join(" ");
}

export function ScoreRing({
  score = 0,
  label = "Trust score",
  size = "default",
  state = "ready",
  valueLabel,
  riskLevel,
}: ScoreRingProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const progress = state === "ready" ? `${clampedScore} ${100 - clampedScore}` : "32 68";
  const displayValue = valueLabel ?? (state === "ready" ? String(clampedScore) : "--");
  const className = scoreRingClassName({ riskLevel, size, state });

  return (
    <div className={className} aria-label={`${label}: ${displayValue}`}>
      <svg viewBox="0 0 120 120" className="score-ring__svg" aria-hidden="true">
        <circle className="score-ring__track" cx="60" cy="60" r="48" />
        <circle
          className="score-ring__progress"
          cx="60"
          cy="60"
          r="48"
          pathLength="100"
          strokeDasharray={progress}
        />
      </svg>
      <div className="score-ring__content">
        <p className="score-ring__label">{label}</p>
        <p className="score-ring__value">{displayValue}</p>
      </div>
    </div>
  );
}
