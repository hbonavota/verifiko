import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ScoreRing } from "./ScoreRing";

beforeEach(() => {
  // Reduced motion skips the count-up animation, so the final score renders at once.
  // jsdom has no matchMedia of its own.
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: vi.fn((query: string) => ({ matches: true, media: query })),
  });
});

describe("ScoreRing", () => {
  it("clamps the score to 0–100 and picks the matching tone", () => {
    const { container, rerender } = render(<ScoreRing score={140} label="Trust score" />);

    expect(screen.getByLabelText("Trust score: 100")).toHaveClass("score-ring--success");
    expect(container.querySelector(".score-ring__progress")).toHaveAttribute(
      "stroke-dasharray",
      "100 0",
    );

    rerender(<ScoreRing score={-20} label="Trust score" />);

    expect(screen.getByLabelText("Trust score: 0")).toHaveClass("score-ring--danger");
  });

  it("shows a neutral placeholder while loading instead of a score", () => {
    render(<ScoreRing score={92} label="Puntuación" state="loading" />);

    const ring = screen.getByLabelText("Puntuación: --");
    expect(ring).toHaveClass("score-ring--neutral", "score-ring--loading");
    expect(ring).toHaveTextContent("Puntuación--");
  });
});
