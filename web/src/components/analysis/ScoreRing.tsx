import { useEffect, useState } from "react";

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
  score,
  size,
  state,
}: Pick<ScoreRingProps, "score" | "size" | "state">) {
  const classes = ["score-ring"];

  if (size === "hero") {
    classes.push("score-ring--hero");
  }

  if (state === "loading") {
    classes.push("score-ring--neutral", "score-ring--loading");
    return classes.join(" ");
  }

  if (state === "idle" || typeof score !== "number" || Number.isNaN(score)) {
    classes.push("score-ring--neutral");
    return classes.join(" ");
  }

  if (score <= 40) {
    classes.push("score-ring--danger");
  } else if (score <= 60) {
    classes.push("score-ring--warning-strong");
  } else if (score <= 80) {
    classes.push("score-ring--warning-soft");
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
  const isReadyNumeric = state === "ready" && valueLabel === undefined;

  // Animate the score counting up from 0 as the result reveals — a small,
  // satisfying payoff for running a check. Skips when reduced motion is set.
  const [animatedScore, setAnimatedScore] = useState(isReadyNumeric ? 0 : clampedScore);
  useEffect(() => {
    if (!isReadyNumeric) {
      setAnimatedScore(clampedScore);
      return;
    }
    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setAnimatedScore(clampedScore);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const duration = 750;
    const tick = (now: number) => {
      const progressT = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progressT, 3);
      setAnimatedScore(clampedScore * eased);
      if (progressT < 1) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [isReadyNumeric, clampedScore]);

  const shownScore = isReadyNumeric ? animatedScore : clampedScore;
  const progress = state === "ready" ? `${shownScore} ${100 - shownScore}` : "32 68";
  const displayValue = valueLabel ?? (state === "ready" ? String(Math.round(shownScore)) : "--");
  const className = scoreRingClassName({ score: clampedScore, size, state });

  return (
    <div className={className} aria-label={`${label}: ${displayValue}`} data-state={state}>
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
