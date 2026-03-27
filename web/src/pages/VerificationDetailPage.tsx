import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { getVerificationById } from "../lib/api";
import { formatVerdict } from "../lib/formatVerdict";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";
import type { VerificationSummary } from "../types/verification";

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

function shortResultExplanation(verification: VerificationSummary) {
  if (verification.riskLevel === "CRITICAL" || verification.riskLevel === "HIGH") {
    return "Do not trust this link until it is reviewed.";
  }

  if (verification.riskLevel === "MEDIUM") {
    return "Review this link before treating it as safe.";
  }

  return "No strong warning signal was retained in this result.";
}

const SCORE_ZONE_LEGEND = [
  { label: "High danger", range: "0-40", tone: "danger" },
  { label: "Dangerous / strong caution", range: "41-60", tone: "warning-strong" },
  { label: "Proceed with caution", range: "61-80", tone: "warning-soft" },
  { label: "No strong insecurity detected", range: "81-100", tone: "success" },
] as const;

function scoreInterpretationCopy(score: number) {
  if (score <= 40) {
    return "This score falls in the highest-danger band and should not be treated as safe.";
  }
  if (score <= 60) {
    return "This score sits in a dangerous band and needs careful review before trust.";
  }
  if (score <= 80) {
    return "This score suggests caution. Review the retained signals before relying on it.";
  }
  return "No strong insecurity was retained in this check, but the result is still not a guarantee.";
}

type VerificationState =
  | { status: "loading" }
  | { status: "ready"; verification: VerificationSummary }
  | { status: "error"; message: string };

export function VerificationDetailPage() {
  const { id } = useParams();
  const [verificationState, setVerificationState] = useState<VerificationState>({ status: "loading" });
  const [isDisclaimerOpen, setIsDisclaimerOpen] = useState(false);

  useEffect(() => {
    if (!id) {
      setVerificationState({ status: "error", message: "Verification id is required." });
      return;
    }

    const verificationId = id;
    let isMounted = true;

    async function loadVerification() {
      setVerificationState({ status: "loading" });

      try {
        const payload = await getVerificationById(verificationId);
        if (!isMounted) {
          return;
        }

        setVerificationState({ status: "ready", verification: adaptApiVerification(payload) });
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setVerificationState({
          status: "error",
          message: error instanceof Error ? error.message : "Verification lookup failed.",
        });
      }
    }

    void loadVerification();

    return () => {
      isMounted = false;
    };
  }, [id]);

  useEffect(() => {
    if (!isDisclaimerOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsDisclaimerOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isDisclaimerOpen]);

  const verification = verificationState.status === "ready" ? verificationState.verification : null;

  useDocumentMeta(
    verification ? verification.subject : "Verification Detail",
    verification
      ? `Review the verification result for ${verification.subject}, including score, signals, and next action.`
      : "Review score, signals, and next action for a verification result.",
  );

  if (verificationState.status === "loading") {
    return (
      <PageShell>
        <SectionTitle
          eyebrow="Verification Detail"
          title="Loading result"
          description="Preparing the verification result."
        />
      </PageShell>
    );
  }

  if (verificationState.status === "error" || !verification) {
    return (
      <PageShell>
        <SectionTitle
          eyebrow="Verification Detail"
          title="Result unavailable"
          description={
            verificationState.status === "error"
              ? verificationState.message
              : "The requested result could not be loaded."
          }
        />
        <Button to="/dashboard" variant="secondary">
          Return to review
        </Button>
      </PageShell>
    );
  }

  const topSignals = [...verification.signals].sort(
    (left, right) => right.scoreContribution - left.scoreContribution,
  );
  const primaryReasons = topSignals.slice(0, 3);
  const clampedScore = Math.max(0, Math.min(100, Number(verification.score) || 0));

  const riskTone = toneForRiskLevel(verification.riskLevel);
  const emphasisTone =
    riskTone === "danger" ? "danger" : riskTone === "success" ? "success" : "warning";

  return (
    <PageShell>
      <section className="verification-detail-header">
        <div className="verification-detail-header__copy">
          <p className="eyebrow">Verification Detail</p>
          <h1 className="serif-heading verification-detail__title">Verification result</h1>
          <p className="muted-copy verification-detail__summary-copy">
            Verdict first. Evidence below.
          </p>
        </div>
        <div className="verification-detail-target">
          <p className="verification-detail-target__label">Target</p>
          <p className="verification-detail-target__value" title={verification.subject}>
            {verification.subject}
          </p>
        </div>
      </section>

      <section className="verification-detail-primary">
        <Card
          eyebrow="Result"
          title={undefined}
          description={undefined}
          tone={emphasisTone}
          className="verification-assessment-card"
        >
          <div className="verification-assessment-card__topline">
            <Badge label={`${verification.riskLevel} RISK`} tone={toneForRiskLevel(verification.riskLevel)} />
            <p className="verification-assessment-card__status">{verification.status}</p>
          </div>

          <div className="verification-assessment-card__hero">
            <ScoreRing label="Trust score" riskLevel={verification.riskLevel} score={verification.score} size="hero" />

            <div className="verification-assessment-card__verdict-block">
              <p className="metric-card__label">Verdict</p>
              <p
                className="verification-assessment-card__verdict"
                title={`Verification result: ${formatVerdict(verification.verdict)}`}
              >
                {formatVerdict(verification.verdict)}
              </p>
              <p className="verification-assessment-card__posture">{verification.executiveSummary.posture}</p>
              <p className="verification-assessment-card__explanation">
                {shortResultExplanation(verification)}
              </p>
              <div className="verification-assessment-card__actions">
                <Button to="/dashboard" variant="primary">
                  Verify another link
                </Button>
                <Button to="/dashboard" variant="secondary">
                  Back to review
                </Button>
              </div>
            </div>
          </div>

          <div className="verification-score-guide" aria-label="Score interpretation guide">
            <div className="verification-score-guide__header">
              <p className="metric-card__label">Score interpretation</p>
              <p className="verification-score-guide__copy">{scoreInterpretationCopy(clampedScore)}</p>
            </div>
            <div className="verification-score-guide__scale" aria-hidden="true">
              <div className="verification-score-guide__track">
                <span className="verification-score-guide__zone verification-score-guide__zone--danger" />
                <span className="verification-score-guide__zone verification-score-guide__zone--warning-strong" />
                <span className="verification-score-guide__zone verification-score-guide__zone--warning-soft" />
                <span className="verification-score-guide__zone verification-score-guide__zone--success" />
              </div>
              <div className="verification-score-guide__ticks">
                <span>0</span>
                <span>40</span>
                <span>60</span>
                <span>80</span>
                <span>100</span>
              </div>
              <div
                className="verification-score-guide__marker"
                style={{ left: `${clampedScore}%` }}
              >
                <span className="verification-score-guide__marker-value">{Math.round(clampedScore)}</span>
              </div>
            </div>
            <div className="verification-score-guide__legend" role="list">
              {SCORE_ZONE_LEGEND.map((item) => (
                <article key={item.range} className="verification-score-guide__legend-item" role="listitem">
                  <span className="verification-score-guide__legend-swatch" data-tone={item.tone} />
                  <div className="verification-score-guide__legend-copy">
                    <p className="verification-score-guide__range">{item.range}</p>
                    <p className="verification-score-guide__label">{item.label}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="verification-assessment-card__pills">
            <StatPill label="Signals retained" value={String(verification.signals.length)} tone="warning" />
            <StatPill
              label="Unresolved items"
              value={String(verification.inconclusive.length)}
              tone={verification.inconclusive.length > 0 ? "danger" : "success"}
            />
          </div>
        </Card>
      </section>

      <section className="verification-detail-grid">
        <div className="verification-detail-main">
          <Card
            eyebrow="Main reasons"
            title="Why this result was flagged"
            description={undefined}
          >
            {primaryReasons.length > 0 ? (
              <div className="summary-reason-list">
                {primaryReasons.map((signal, index) => (
                  <article key={signal.id} className="summary-reason-card">
                    <div className="summary-reason-card__topline">
                      <span className="summary-reason-card__index">{index + 1}</span>
                      <Badge label={signal.severity} tone={toneForRiskLevel(signal.severity)} />
                    </div>
                    <p className="summary-reason-card__title">{signal.title}</p>
                    <p className="summary-reason-card__copy">{signal.reason}</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="verification-summary-panel">
                <p className="verification-summary-panel__headline">No major warning reason surfaced</p>
                <p className="verification-summary-panel__copy">
                  The supporting detail below is mainly useful for context.
                </p>
              </div>
            )}
          </Card>

          <Card
            eyebrow="Result context"
            title="Record details"
            description={undefined}
            className="verification-detail-meta-card"
          >
            <div className="verification-detail-meta-grid verification-detail-meta-grid--compact">
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">Verification ID</p>
                <p className="verification-detail-meta-item__value">{verification.id}</p>
              </article>
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">Verified target</p>
                <p className="verification-detail-meta-item__value">{verification.normalizedInput}</p>
              </article>
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">Executed at</p>
                <p className="verification-detail-meta-item__value">{formatTimestamp(verification.createdAt)}</p>
              </article>
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">Current status</p>
                <p className="verification-detail-meta-item__value">{verification.status}</p>
              </article>
            </div>
          </Card>

          <section className="technical-analysis-section">
            <div className="technical-analysis-section__header">
              <p className="eyebrow">Evidence</p>
              <h2 className="serif-heading technical-analysis-section__title">Detailed signal review</h2>
              <p className="muted-copy technical-analysis-section__copy">
                Full evidence and the decision path are shown below.
              </p>
            </div>

            <Card
              eyebrow="Signal review"
              title="Signals shaping the current verdict"
              description={undefined}
            >
              <div className="signal-review-list">
                {topSignals.map((signal) => (
                  <article key={signal.id} className="signal-review-card">
                    <div className="signal-review-card__header">
                      <div>
                        <p className="signal-review-card__title">{signal.title}</p>
                        <p className="signal-review-card__description">{signal.description}</p>
                      </div>
                      <div className="signal-review-card__score">
                        <p className="signal-review-card__score-label">Contribution</p>
                        <p className="signal-review-card__score-value">-{signal.scoreContribution}</p>
                      </div>
                    </div>

                    <div className="signal-review-card__meta">
                      <Badge label={signal.severity} tone={toneForRiskLevel(signal.severity)} />
                      <span className="signal-review-card__meta-item">{signal.category}</span>
                      <span className="signal-review-card__meta-item">{signal.confidence}% confidence</span>
                      <span className="signal-review-card__meta-item">{signal.source}</span>
                    </div>

                    <div className="signal-review-card__reasoning">
                      <div>
                        <p className="signal-review-card__label">Why it mattered</p>
                        <p className="signal-review-card__reason">{signal.reason}</p>
                      </div>
                      <div>
                        <p className="signal-review-card__label">Supporting observation</p>
                        <ul className="signal-review-card__evidence">
                          {signal.evidence.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </Card>

            <section className="verification-detail-analysis-grid">
              <Card
                eyebrow="Evidence used"
                title="Observed facts"
                description={undefined}
              >
                <div className="evidence-grid">
                  <div className="evidence-block">
                    <p className="evidence-block__label">Observations</p>
                    <ul className="evidence-block__list">
                      {verification.evidenceSummary.observed.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="evidence-block">
                    <p className="evidence-block__label">Sources</p>
                    <ul className="evidence-block__list">
                      {verification.evidenceSummary.sources.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="evidence-block">
                    <p className="evidence-block__label">Supporting context</p>
                    <ul className="evidence-block__list">
                      {verification.evidenceSummary.supportingContext.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Card>

              <Card
                eyebrow="What remains uncertain"
                title="Confidence limits"
                description={undefined}
              >
                <div className="inconclusive-list">
                  {verification.inconclusive.map((item) => (
                    <article key={item.id} className="inconclusive-card">
                      <p className="inconclusive-card__title">{item.title}</p>
                      <p className="inconclusive-card__detail">{item.detail}</p>
                      <div className="inconclusive-card__next">
                        <p className="inconclusive-card__label">What would improve certainty</p>
                        <p className="inconclusive-card__next-copy">{item.nextEvidence}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </Card>
            </section>

            <Card
              eyebrow="Decision trace"
              title="Decision path"
              description={undefined}
            >
              <div className="decision-trace">
                {verification.decisionTrace.map((step) => (
                  <article key={step.id} className="decision-trace__item">
                    <div className="decision-trace__marker" />
                    <div className="decision-trace__content">
                      <div className="decision-trace__header">
                        <p className="decision-trace__label">{step.label}</p>
                        {step.timestamp ? (
                          <p className="decision-trace__timestamp">{formatTimestamp(step.timestamp)}</p>
                        ) : null}
                      </div>
                      <p className="decision-trace__detail">{step.detail}</p>
                      <p className="decision-trace__outcome">{step.outcome}</p>
                    </div>
                  </article>
                ))}
              </div>
            </Card>
          </section>
        </div>

        <aside className="verification-detail-rail">
          <Card
            eyebrow="Recommended action"
            title={verification.recommendation.title}
            description={undefined}
            tone={emphasisTone}
            className="verification-action-card"
          >
            <div className="verification-action-card__stack">
              <p className="verification-action-card__copy">{verification.recommendation.detail}</p>
              <div className="action-stack">
                <Button to="/dashboard" variant="primary">
                  Back to review
                </Button>
                <Button to="/dashboard#signals" variant="ghost">
                  View signals
                </Button>
              </div>
            </div>
          </Card>

          <Card
            eyebrow="Context"
            title="Result context"
            description={undefined}
            className="verification-context-card"
          >
            <div className="verification-context-card__stack">
              <StatPill label="Evidence sources" value={String(verification.evidenceSummary.sources.length)} />
              <StatPill label="Observed findings" value={String(verification.evidenceSummary.observed.length)} />
              <StatPill
                label="Open questions"
                value={String(verification.inconclusive.length)}
                tone={verification.inconclusive.length > 0 ? "warning" : "success"}
              />
            </div>
            <div className="verification-context-card__notes">
              <p className="verification-action-card__label">Assessment note</p>
              <p className="notes-panel__text">{verification.analystNote}</p>
            </div>
          </Card>
        </aside>
      </section>

      <section className="verification-detail-footer-note">
        <Card
          action={
            <Button onClick={() => setIsDisclaimerOpen(true)} variant="secondary">
              Learn more
            </Button>
          }
          eyebrow="Important"
          title="A clean result is still not a guarantee"
          description="This verification reflects the checks completed at one moment in time."
          className="verification-disclaimer-card"
        >
          <p className="verification-disclaimer-card__copy">
            A stronger score means the completed checks did not retain major warning signals. It does not prove ownership,
            future safety, or that broader context is complete.
          </p>
        </Card>
      </section>

      {!isDisclaimerOpen ? (
        <Button className="verification-disclaimer-float" onClick={() => setIsDisclaimerOpen(true)} variant="secondary">
          Analysis has limits. Learn more
        </Button>
      ) : null}

      {isDisclaimerOpen ? (
        <div
          className="verification-modal"
          role="dialog"
          aria-label="Why a high score is not a guarantee of safety"
          aria-modal="true"
        >
          <button
            aria-label="Close explanation"
            className="verification-modal__backdrop"
            onClick={() => setIsDisclaimerOpen(false)}
            type="button"
          />
          <Card
            eyebrow="How to read this result"
            title="Why a high score is not a guarantee of safety"
            description="This result should guide your decision, not replace judgment."
            action={
              <Button onClick={() => setIsDisclaimerOpen(false)} variant="ghost">
                Close
              </Button>
            }
            className="verification-modal__panel"
          >
            <div className="verification-modal__content">
              <article className="verification-modal__point">
                <p className="verification-modal__point-title">This result is a technical snapshot</p>
                <p className="verification-modal__point-copy">
                  The score summarizes what the engine retained during this verification run. It does not represent the
                  full history of the domain or every possible risk.
                </p>
              </article>
              <article className="verification-modal__point">
                <p className="verification-modal__point-title">Some threats change behavior over time</p>
                <p className="verification-modal__point-copy">
                  A link can look clean during one check and behave differently later because the destination, payload, or
                  infrastructure changes.
                </p>
              </article>
              <article className="verification-modal__point">
                <p className="verification-modal__point-title">Dynamic delivery can hide risk</p>
                <p className="verification-modal__point-copy">
                  Some pages use cloaking, conditional redirects, or dynamic content, so they may present differently to
                  different users or at different times.
                </p>
              </article>
              <article className="verification-modal__point">
                <p className="verification-modal__point-title">Use the score to support judgment, not replace it</p>
                <p className="verification-modal__point-copy">
                  The most reliable interpretation comes from the score, retained signals, and confidence limits taken
                  together with normal human review.
                </p>
              </article>
            </div>
          </Card>
        </div>
      ) : null}
    </PageShell>
  );
}
