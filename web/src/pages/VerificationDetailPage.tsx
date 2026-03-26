import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { getVerificationById } from "../lib/api";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";
import type { VerificationSummary } from "../types/verification";

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

function plainLanguageSummary(verification: VerificationSummary) {
  if (verification.riskLevel === "CRITICAL" || verification.riskLevel === "HIGH") {
    return "This target shows strong warning signs.";
  }

  if (verification.riskLevel === "MEDIUM") {
    return "This target needs a closer review.";
  }

  return "This target currently appears low risk.";
}

function shortResultExplanation(verification: VerificationSummary) {
  if (verification.riskLevel === "CRITICAL" || verification.riskLevel === "HIGH") {
    return "Treat this target as suspicious until reviewed.";
  }

  if (verification.riskLevel === "MEDIUM") {
    return "Review this target before treating it as trusted.";
  }

  return "No strong warning signs were retained in this run.";
}

function topReasonSummary(verification: VerificationSummary) {
  if (verification.signals.length === 0) {
    return "No strong warning signal was retained from the current verification run.";
  }

  return "The strongest retained reasons are shown first so the result can be understood before opening the full trace.";
}

type VerificationState =
  | { status: "loading" }
  | { status: "ready"; verification: VerificationSummary }
  | { status: "error"; message: string };

export function VerificationDetailPage() {
  const { id } = useParams();
  const [verificationState, setVerificationState] = useState<VerificationState>({ status: "loading" });

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

  const verification = verificationState.status === "ready" ? verificationState.verification : null;

  useDocumentMeta(
    verification ? verification.subject : "Verification Detail",
    verification
      ? `Evidence review for ${verification.subject}, including score rationale, signal materiality, unresolved items, and recommended action.`
      : "Verification detail route for reviewing score rationale, supporting evidence, and next-step guidance.",
  );

  if (verificationState.status === "loading") {
    return (
      <PageShell>
        <SectionTitle
          eyebrow="Verification Detail"
          title="Loading verification result"
          description="Loading the verification result for this page."
        />
      </PageShell>
    );
  }

  if (verificationState.status === "error" || !verification) {
    return (
      <PageShell>
        <SectionTitle
          eyebrow="Verification Detail"
          title="Verification result unavailable"
          description={
            verificationState.status === "error"
              ? verificationState.message
              : "The requested verification could not be loaded."
          }
        />
        <Button to="/dashboard" variant="secondary">
          Return to dashboard
        </Button>
      </PageShell>
    );
  }

  const topSignals = [...verification.signals].sort(
    (left, right) => right.scoreContribution - left.scoreContribution,
  );
  const primaryReasons = topSignals.slice(0, 3);

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
            Trust score first. Supporting detail below.
          </p>
        </div>
        <div className="verification-detail-target">
          <p className="verification-detail-target__label">Target</p>
          <p className="verification-detail-target__value">{verification.subject}</p>
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
              <p className="metric-card__label">What this means</p>
              <p className="verification-assessment-card__verdict">{verification.verdict}</p>
              <p className="verification-assessment-card__posture">{verification.executiveSummary.posture}</p>
              <p className="verification-assessment-card__explanation">
                {shortResultExplanation(verification)}
              </p>
              <div className="verification-assessment-card__actions">
                <Button to="/dashboard" variant="primary">
                  Analyze another target
                </Button>
                <Button to="/dashboard" variant="secondary">
                  Back to dashboard
                </Button>
              </div>
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
            description={topReasonSummary(verification)}
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
                  The current verification did not retain a strong signal, so the supporting detail below is mainly useful for context.
                </p>
              </div>
            )}
          </Card>

          <Card
            eyebrow="Verification context"
            title="Run details"
            description="Compact record metadata kept below the summary for traceability."
            className="verification-detail-meta-card"
          >
            <div className="verification-detail-meta-grid verification-detail-meta-grid--compact">
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">Verification ID</p>
                <p className="verification-detail-meta-item__value">{verification.id}</p>
              </article>
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">Analyzed target</p>
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
              <p className="eyebrow">Technical analysis</p>
              <h2 className="serif-heading technical-analysis-section__title">Detailed signal review</h2>
              <p className="muted-copy technical-analysis-section__copy">
                Full evidence, signal weighting, and the current verification trace remain available below for analyst-style review.
              </p>
            </div>

            <Card
              eyebrow="Signal review"
              title="Signals shaping the current verdict"
              description="All retained signals are listed here with contribution, confidence, and supporting observations."
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
                title="Observed facts and supporting context"
                description="Traceability panel showing what was observed, what contributed, and where the evidence came from."
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
                eyebrow="What remains inconclusive"
                title="Confidence limits still affecting the result"
                description="Unresolved items are kept explicit so the current verdict does not read as more certain than the evidence supports."
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
              title="Audit timeline"
              description="Step-by-step reasoning path from normalized input to final explanation output."
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
            description="Primary operational step derived from the current evidence posture."
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
                  Open signal review
                </Button>
              </div>
            </div>
          </Card>

          <Card
            eyebrow="Traceability"
            title="Review context"
            description="Compact context strip for the current verification record."
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
              <p className="verification-action-card__label">Analyst note</p>
              <p className="notes-panel__text">{verification.analystNote}</p>
            </div>
          </Card>
        </aside>
      </section>
    </PageShell>
  );
}
