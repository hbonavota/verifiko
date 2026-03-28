import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { useAuth } from "../lib/auth";
import { formatRiskLevel, formatVerdict, formatVerificationStatus } from "../lib/formatVerdict";
import { getOwnedVerificationById } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";
import type { ApiVerification, VerificationSummary } from "../types/verification";

function formatTimestamp(value: string, locale: string) {
  return new Date(value).toLocaleString(locale);
}

function shortResultExplanation(
  verification: VerificationSummary,
  explanations: {
    severe: string;
    medium: string;
    low: string;
  },
) {
  if (verification.riskLevel === "CRITICAL" || verification.riskLevel === "HIGH") {
    return explanations.severe;
  }

  if (verification.riskLevel === "MEDIUM") {
    return explanations.medium;
  }

  return explanations.low;
}

function scoreInterpretationCopy(
  score: number,
  copy: {
    highDanger: string;
    strongCaution: string;
    caution: string;
    safe: string;
  },
) {
  if (score <= 40) {
    return copy.highDanger;
  }
  if (score <= 60) {
    return copy.strongCaution;
  }
  if (score <= 80) {
    return copy.caution;
  }
  return copy.safe;
}

type VerificationState =
  | { status: "loading" }
  | { status: "ready"; verification: VerificationSummary }
  | { status: "error"; message: string };

interface VerificationDetailLocationState {
  verification?: ApiVerification;
}

export function VerificationDetailPage() {
  const { copy, language, locale } = useI18n();
  const { authReady, currentUser } = useAuth();
  const { id } = useParams();
  const location = useLocation();
  const [verificationState, setVerificationState] = useState<VerificationState>({ status: "loading" });
  const [isDisclaimerOpen, setIsDisclaimerOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;

    if (!id) {
      setVerificationState({ status: "error", message: copy.detail.verificationIdRequired });
      return;
    }

    const navigationState = location.state as VerificationDetailLocationState | null;
    const payload = navigationState?.verification;

    if (payload && payload.id === id) {
      setVerificationState({
        status: "ready",
        verification: adaptApiVerification(payload, language),
      });
      return () => {
        isMounted = false;
      };
    }

    if (!authReady) {
      return () => {
        isMounted = false;
      };
    }

    if (!currentUser) {
      setVerificationState({
        status: "error",
        message: copy.detail.requestedResultUnavailable,
      });
      return () => {
        isMounted = false;
      };
    }

    void getOwnedVerificationById(id)
      .then((verification) => {
        if (!isMounted) {
          return;
        }
        setVerificationState({
          status: "ready",
          verification: adaptApiVerification(verification, language),
        });
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setVerificationState({
          status: "error",
          message: copy.detail.requestedResultUnavailable,
        });
      });

    return () => {
      isMounted = false;
    };
  }, [
    authReady,
    copy.detail.requestedResultUnavailable,
    copy.detail.verificationIdRequired,
    currentUser,
    id,
    language,
    location.state,
  ]);

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
    verification ? verification.subject : copy.detail.metaTitleFallback,
    verification
      ? `${copy.detail.metaDescriptionLoaded} ${verification.subject}.`
      : copy.detail.metaDescriptionFallback,
  );

  if (verificationState.status === "loading") {
    return (
      <PageShell>
        <SectionTitle
          eyebrow={copy.detail.eyebrow}
          title={copy.common.loadingResult}
          description={copy.detail.preparingResult}
        />
      </PageShell>
    );
  }

  if (verificationState.status === "error" || !verification) {
    return (
      <PageShell>
        <SectionTitle
          eyebrow={copy.detail.eyebrow}
          title={copy.common.resultUnavailable}
          description={
            verificationState.status === "error"
              ? verificationState.message
              : copy.detail.requestedResultUnavailable
          }
        />
        <Button to="/dashboard" variant="secondary">
          {copy.common.backToReview}
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
          <p className="eyebrow">{copy.detail.eyebrow}</p>
          <h1 className="serif-heading verification-detail__title">{copy.detail.title}</h1>
          <p className="muted-copy verification-detail__summary-copy">
            {copy.detail.summaryCopy}
          </p>
        </div>
        <div className="verification-detail-target">
          <p className="verification-detail-target__label">{copy.detail.target}</p>
          <p className="verification-detail-target__value" title={verification.subject}>
            {verification.subject}
          </p>
        </div>
      </section>

      <section className="verification-detail-primary">
        <Card
          eyebrow={copy.detail.result}
          title={undefined}
          description={undefined}
          tone={emphasisTone}
          className="verification-assessment-card"
        >
          <div className="verification-assessment-card__topline">
            <Badge
              label={`${formatRiskLevel(verification.riskLevel, language)} ${copy.common.risk}`}
              tone={toneForRiskLevel(verification.riskLevel)}
            />
            <p className="verification-assessment-card__status">{formatVerificationStatus(verification.status, language)}</p>
          </div>

          <div className="verification-assessment-card__hero">
            <ScoreRing label={copy.common.trustScore} riskLevel={verification.riskLevel} score={verification.score} size="hero" />

            <div className="verification-assessment-card__verdict-block">
              <p className="metric-card__label">{copy.common.verdict}</p>
              <p
                className="verification-assessment-card__verdict"
                title={`${copy.common.verificationResult}: ${formatVerdict(verification.verdict, language)}`}
              >
                {formatVerdict(verification.verdict, language)}
              </p>
              <p className="verification-assessment-card__posture">{verification.executiveSummary.posture}</p>
              <p className="verification-assessment-card__explanation">
                {shortResultExplanation(verification, copy.detail.resultExplanations)}
              </p>
              <div className="verification-assessment-card__actions">
                <Button to="/dashboard" variant="primary">
                  {copy.common.verifyAnotherLink}
                </Button>
                <Button to="/dashboard" variant="secondary">
                  {copy.common.backToReview}
                </Button>
              </div>
            </div>
          </div>

          <div className="verification-score-guide" aria-label={copy.detail.scoreInterpretation}>
            <div className="verification-score-guide__header">
              <p className="metric-card__label">{copy.detail.scoreInterpretation}</p>
              <p className="verification-score-guide__copy">{scoreInterpretationCopy(clampedScore, copy.detail.scoreGuide)}</p>
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
              {copy.detail.scoreGuide.legend.map((item) => (
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
            <StatPill label={copy.detail.signalsRetained} value={String(verification.signals.length)} tone="warning" />
            <StatPill
              label={copy.detail.openQuestions}
              value={String(verification.inconclusive.length)}
              tone={verification.inconclusive.length > 0 ? "danger" : "success"}
            />
          </div>
        </Card>
      </section>

      <section className="verification-detail-grid">
        <div className="verification-detail-main">
          <Card
            eyebrow={copy.detail.mainReasons}
            title={copy.detail.whyFlagged}
            description={undefined}
          >
            {primaryReasons.length > 0 ? (
              <div className="summary-reason-list">
                {primaryReasons.map((signal, index) => (
                  <article key={signal.id} className="summary-reason-card">
                    <div className="summary-reason-card__topline">
                      <span className="summary-reason-card__index">{index + 1}</span>
                      <Badge
                        label={formatRiskLevel(signal.severity, language)}
                        tone={toneForRiskLevel(signal.severity)}
                      />
                    </div>
                    <p className="summary-reason-card__title">{signal.title}</p>
                    <p className="summary-reason-card__copy">{signal.reason}</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="verification-summary-panel">
                <p className="verification-summary-panel__headline">{copy.detail.noMajorReason}</p>
                <p className="verification-summary-panel__copy">{copy.detail.noMajorReasonCopy}</p>
              </div>
            )}
          </Card>

          <Card
            eyebrow={copy.detail.resultContext}
            title={copy.detail.recordDetails}
            description={undefined}
            className="verification-detail-meta-card"
          >
            <div className="verification-detail-meta-grid verification-detail-meta-grid--compact">
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">{copy.detail.verificationId}</p>
                <p className="verification-detail-meta-item__value">{verification.id}</p>
              </article>
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">{copy.detail.verifiedTarget}</p>
                <p className="verification-detail-meta-item__value">{verification.normalizedInput}</p>
              </article>
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">{copy.detail.executedAt}</p>
                <p className="verification-detail-meta-item__value">{formatTimestamp(verification.createdAt, locale)}</p>
              </article>
              <article className="verification-detail-meta-item">
                <p className="verification-detail-meta-item__label">{copy.detail.currentStatus}</p>
                <p className="verification-detail-meta-item__value">{formatVerificationStatus(verification.status, language)}</p>
              </article>
            </div>
          </Card>

          <section className="technical-analysis-section">
            <div className="technical-analysis-section__header">
              <p className="eyebrow">{copy.detail.evidenceEyebrow}</p>
              <h2 className="serif-heading technical-analysis-section__title">{copy.detail.detailedReviewTitle}</h2>
              <p className="muted-copy technical-analysis-section__copy">
                {copy.detail.detailedReviewCopy}
              </p>
            </div>

            <Card
              eyebrow={copy.detail.signalReview}
              title={copy.detail.signalReviewTitle}
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
                        <p className="signal-review-card__score-label">{copy.detail.contribution}</p>
                        <p className="signal-review-card__score-value">-{signal.scoreContribution}</p>
                      </div>
                    </div>

                    <div className="signal-review-card__meta">
                      <Badge
                        label={formatRiskLevel(signal.severity, language)}
                        tone={toneForRiskLevel(signal.severity)}
                      />
                      <span className="signal-review-card__meta-item">{signal.category}</span>
                      <span className="signal-review-card__meta-item">{`${signal.confidence}${copy.detail.confidenceSuffix}`}</span>
                      <span className="signal-review-card__meta-item">{signal.source}</span>
                    </div>

                    <div className="signal-review-card__reasoning">
                      <div>
                        <p className="signal-review-card__label">{copy.detail.whyItMattered}</p>
                        <p className="signal-review-card__reason">{signal.reason}</p>
                      </div>
                      <div>
                        <p className="signal-review-card__label">{copy.detail.supportingObservation}</p>
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
                eyebrow={copy.detail.evidenceUsed}
                title={copy.detail.observedFacts}
                description={undefined}
              >
                <div className="evidence-grid">
                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.detail.observations}</p>
                    <ul className="evidence-block__list">
                      {verification.evidenceSummary.observed.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.dashboard.sources}</p>
                    <ul className="evidence-block__list">
                      {verification.evidenceSummary.sources.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.detail.supportingContext}</p>
                    <ul className="evidence-block__list">
                      {verification.evidenceSummary.supportingContext.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Card>

              <Card
                eyebrow={copy.detail.uncertaintyEyebrow}
                title={copy.detail.confidenceLimits}
                description={undefined}
              >
                <div className="inconclusive-list">
                  {verification.inconclusive.map((item) => (
                    <article key={item.id} className="inconclusive-card">
                      <p className="inconclusive-card__title">{item.title}</p>
                      <p className="inconclusive-card__detail">{item.detail}</p>
                      <div className="inconclusive-card__next">
                        <p className="inconclusive-card__label">{copy.detail.whatImprovesCertainty}</p>
                        <p className="inconclusive-card__next-copy">{item.nextEvidence}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </Card>
            </section>

            <Card
              eyebrow={copy.detail.decisionTrace}
              title={copy.detail.decisionPath}
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
                          <p className="decision-trace__timestamp">{formatTimestamp(step.timestamp, locale)}</p>
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
            eyebrow={copy.detail.recommendedAction}
            title={verification.recommendation.title}
            description={undefined}
            tone={emphasisTone}
            className="verification-action-card"
          >
            <div className="verification-action-card__stack">
              <p className="verification-action-card__copy">{verification.recommendation.detail}</p>
              <div className="action-stack">
                <Button to="/dashboard" variant="primary">
                  {copy.common.backToReview}
                </Button>
                <Button to="/dashboard#signals" variant="ghost">
                  {copy.common.viewSignals}
                </Button>
              </div>
            </div>
          </Card>

          <Card
            eyebrow={copy.common.context}
            title={copy.detail.contextCardTitle}
            description={undefined}
            className="verification-context-card"
          >
            <div className="verification-context-card__stack">
              <StatPill label={copy.detail.evidenceSources} value={String(verification.evidenceSummary.sources.length)} />
              <StatPill label={copy.detail.observedFindings} value={String(verification.evidenceSummary.observed.length)} />
              <StatPill
                label={copy.detail.openQuestions}
                value={String(verification.inconclusive.length)}
                tone={verification.inconclusive.length > 0 ? "warning" : "success"}
              />
            </div>
            <div className="verification-context-card__notes">
              <p className="verification-action-card__label">{copy.detail.assessmentNote}</p>
              <p className="notes-panel__text">{verification.analystNote}</p>
            </div>
          </Card>
        </aside>
      </section>

      <section className="verification-detail-footer-note">
        <Card
          action={
            <Button onClick={() => setIsDisclaimerOpen(true)} variant="secondary">
              {copy.common.learnMore}
            </Button>
          }
          eyebrow={copy.common.important}
          title={copy.detail.disclaimerTitle}
          description={copy.detail.disclaimerDescription}
          className="verification-disclaimer-card"
        >
          <p className="verification-disclaimer-card__copy">{copy.detail.disclaimerCopy}</p>
        </Card>
      </section>

      {!isDisclaimerOpen ? (
        <Button className="verification-disclaimer-float" onClick={() => setIsDisclaimerOpen(true)} variant="secondary">
          {copy.detail.disclaimerFloat}
        </Button>
      ) : null}

      {isDisclaimerOpen ? (
        <div
          className="verification-modal"
          role="dialog"
          aria-label={copy.detail.modalLabel}
          aria-modal="true"
        >
          <button
            aria-label={copy.common.close}
            className="verification-modal__backdrop"
            onClick={() => setIsDisclaimerOpen(false)}
            type="button"
          />
          <Card
            eyebrow={copy.detail.modalEyebrow}
            title={copy.detail.modalTitle}
            description={copy.detail.modalDescription}
            action={
              <Button onClick={() => setIsDisclaimerOpen(false)} variant="ghost">
                {copy.common.close}
              </Button>
            }
            className="verification-modal__panel"
          >
            <div className="verification-modal__content">
              {copy.detail.modalPoints.map((point) => (
                <article key={point.title} className="verification-modal__point">
                  <p className="verification-modal__point-title">{point.title}</p>
                  <p className="verification-modal__point-copy">{point.copy}</p>
                </article>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </PageShell>
  );
}
