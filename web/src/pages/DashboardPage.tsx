import { useEffect, useState } from "react";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { listVerifications } from "../lib/api";
import { formatRiskLevel, formatVerdict } from "../lib/formatVerdict";
import { useI18n } from "../lib/i18n";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";
import type { RiskLevel, VerificationSummary } from "../types/verification";

function toneForCount(riskLevel: RiskLevel) {
  return toneForRiskLevel(riskLevel);
}

export function DashboardPage() {
  const { copy, language, locale } = useI18n();
  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);

  useDocumentMeta(
    copy.dashboard.metaTitle,
    copy.dashboard.metaDescription,
  );

  useEffect(() => {
    let isMounted = true;

    async function loadVerifications() {
      try {
        const payload = await listVerifications();
        if (!isMounted) {
          return;
        }

        setVerifications(payload.map((verification) => adaptApiVerification(verification, language)));
      } catch {
        if (!isMounted) {
          return;
        }

        setVerifications([]);
      }
    }

    void loadVerifications();

    return () => {
      isMounted = false;
    };
  }, [language]);

  const activeVerification = verifications[0] ?? null;

  const activeReasons =
    activeVerification && activeVerification.signals.length > 0
      ? activeVerification.signals.slice(0, 3).map((signal) => signal.reason)
      : [copy.dashboard.noRecentAnalysis];

  return (
    <PageShell>
      <SectionTitle
        eyebrow={copy.dashboard.eyebrow}
        title={copy.dashboard.title}
        description={copy.dashboard.description}
      />

      <Card
        eyebrow={copy.dashboard.newVerification}
        title={copy.dashboard.verifyAnotherLink}
        description={undefined}
        tone="success"
        id="verifications"
        className="dashboard-intake-card"
      >
        <AnalyzeUrlForm
          buttonLabel={copy.analyzeForm.buttonLabel}
          className="dashboard-intake"
          hint={copy.analyzeForm.hint}
          inputClassName="dashboard-intake__input-control"
          inputLabel={copy.dashboard.link}
          placeholder={copy.analyzeForm.placeholder}
        />
      </Card>

      <Card
        eyebrow={copy.dashboard.latestResult}
        title={activeVerification ? copy.common.trustScore : copy.dashboard.noAnalysesYet}
        description={undefined}
        tone="warning"
        className="dashboard-assessment-card"
      >
        {activeVerification ? (
          <div className="dashboard-card-stack">
            <div className="dashboard-assessment-card__hero">
              <ScoreRing
                label={copy.common.trustScore}
                riskLevel={activeVerification.riskLevel}
                score={activeVerification.score}
                size="hero"
              />
              <div className="dashboard-assessment-card__summary">
                <p className="dashboard-card__subject" title={activeVerification.subject}>
                  {activeVerification.subject}
                </p>
                <div className="dashboard-card__status-row">
                  <Badge
                    label={formatRiskLevel(activeVerification.riskLevel, language)}
                    tone={toneForRiskLevel(activeVerification.riskLevel)}
                  />
                </div>
                <p className="metric-card__label">{copy.dashboard.verdict}</p>
                <p className="dashboard-card__verdict" title={activeVerification.verdict}>
                  {formatVerdict(activeVerification.verdict, language)}
                </p>
                <p className="dashboard-card__posture">{activeVerification.executiveSummary.posture}</p>
                <div className="dashboard-assessment-card__actions">
                  <Button to={`/verifications/${activeVerification.id}`} variant="primary">
                    {copy.common.viewResult}
                  </Button>
                </div>
              </div>
            </div>

            <div className="dashboard-card-headline dashboard-card-headline--muted">
              <div className="dashboard-card-pills">
                <StatPill label={copy.dashboard.signalsCount} value={String(activeVerification.signals.length)} tone="warning" />
                <StatPill label={copy.dashboard.openQuestions} value={String(activeVerification.inconclusive.length)} tone="danger" />
              </div>
            </div>
          </div>
        ) : (
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">{copy.dashboard.status}</p>
                <p className="dashboard-card__target">{copy.dashboard.readyForFirstVerification}</p>
              </div>
              <Badge label={copy.dashboard.empty.toUpperCase()} tone="neutral" />
            </div>
          </div>
        )}
      </Card>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <Card
            eyebrow={copy.dashboard.signalBreakdown}
            title={activeVerification ? copy.dashboard.signalsInThisResult : copy.dashboard.signalsUnavailable}
            description={undefined}
            id="signals"
          >
            {activeVerification ? (
              <div className="signal-table-wrap">
                <div className="signal-table">
                  <div className="signal-table__header">
                    <span>{copy.dashboard.signalName}</span>
                    <span>{copy.dashboard.category}</span>
                    <span>{copy.dashboard.severity}</span>
                    <span>{copy.dashboard.confidence}</span>
                    <span>{copy.dashboard.scoreContribution}</span>
                    <span>{copy.dashboard.status}</span>
                  </div>
                  {activeVerification.signals.map((signal) => (
                    <article key={signal.id} className="signal-table__row">
                      <div className="signal-table__identity">
                        <p className="signal-table__name">{signal.title}</p>
                        <p className="signal-table__subcopy">{signal.description}</p>
                      </div>
                      <span className="signal-table__value" data-label={copy.dashboard.category}>
                        {signal.category}
                      </span>
                      <div className="signal-table__cell" data-label={copy.dashboard.severity}>
                        <Badge
                          label={formatRiskLevel(signal.severity, language)}
                          tone={toneForRiskLevel(signal.severity)}
                        />
                      </div>
                      <span className="signal-table__value" data-label={copy.dashboard.confidence}>
                        {signal.confidence}%
                      </span>
                      <span className="signal-table__value" data-label={copy.dashboard.scoreContribution}>
                        -{signal.scoreContribution}
                      </span>
                      <div className="signal-table__cell" data-label={copy.dashboard.status}>
                        <Badge label={signal.status} tone={toneForRiskLevel(signal.severity)} />
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.noResultAvailableYet}</p>
            )}
          </Card>

          <section className="dashboard-inspection-grid">
            <Card
              eyebrow={copy.dashboard.whyFlagged}
              title={copy.dashboard.mostInfluentialSignals}
              description={undefined}
            >
              <div className="support-list">
                {activeReasons.map((reason, index) => (
                  <article key={reason} className="support-list__item support-list__item--plain">
                    <div>
                      <p className="support-list__title">{`${copy.dashboard.materialFactor} ${index + 1}`}</p>
                      <p className="support-list__description">{reason}</p>
                    </div>
                  </article>
                ))}
              </div>
            </Card>

            <Card
              eyebrow={copy.dashboard.evidenceSnapshot}
              title={copy.dashboard.evidenceSnapshotTitle}
              description={undefined}
            >
              {activeVerification ? (
                <div className="evidence-grid">
                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.dashboard.observed}</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.observed.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.dashboard.sources}</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.sources.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.dashboard.unresolved}</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.unresolved.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <p className="metric-card__detail">{copy.dashboard.evidenceAppearsLater}</p>
              )}
            </Card>
          </section>

          <Card
            eyebrow={copy.dashboard.decisionTrace}
            title={copy.dashboard.scoreGenerationSequence}
            description={undefined}
            id="cases"
          >
            {activeVerification ? (
              <div className="decision-trace">
                {activeVerification.decisionTrace.map((step) => (
                  <article key={step.id} className="decision-trace__item">
                    <div className="decision-trace__marker" />
                    <div className="decision-trace__content">
                      <p className="decision-trace__label">{step.label}</p>
                      <p className="decision-trace__detail">{step.detail}</p>
                      <p className="decision-trace__outcome">{step.outcome}</p>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.decisionTraceAppearsLater}</p>
            )}
          </Card>

          <Card
            eyebrow={copy.dashboard.caseRecommendation}
            title={copy.dashboard.suggestedNextAction}
            description={undefined}
            tone="warning"
          >
            {activeVerification ? (
              <div className="recommendation-panel">
                <p className="recommendation-panel__headline">{activeVerification.recommendation.title}</p>
                <p className="recommendation-panel__copy">{activeVerification.recommendation.detail}</p>
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.recommendationAppearsLater}</p>
            )}
          </Card>
        </div>

        <aside className="dashboard-rail">
          <Card
            eyebrow={copy.dashboard.recentAnalyses}
            title={copy.dashboard.latestResults}
            description={undefined}
            className="dashboard-rail-card"
          >
            {verifications.length > 0 ? (
              <div className="activity-feed">
                {verifications.slice(0, 5).map((verification) => (
                  <article key={verification.id} className="activity-feed__item">
                    <div className="activity-feed__row">
                      <p className="activity-feed__title" title={verification.subject}>{verification.subject}</p>
                      <span className={`activity-feed__actor activity-feed__actor--${toneForCount(verification.riskLevel)}`}>
                        {formatRiskLevel(verification.riskLevel, language)}
                      </span>
                    </div>
                    <p className="activity-feed__detail">{verification.summary}</p>
                    <p className="activity-feed__timestamp">
                      {new Date(verification.createdAt).toLocaleString(locale)}
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="metric-card__detail">{copy.common.noResultsYet}</p>
            )}
          </Card>

          <Card
            eyebrow={copy.dashboard.suggestedNextStep}
            title={copy.dashboard.whatToDoNext}
            description={undefined}
            tone="warning"
            className="dashboard-rail-card"
          >
            {activeVerification ? (
              <div className="notes-panel">
                <p className="recommendation-panel__headline">{activeVerification.recommendation.title}</p>
                <p className="notes-panel__text">{activeVerification.recommendation.detail}</p>
                <p className="notes-panel__meta">{activeVerification.executiveSummary.operationalImpact}</p>
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.nextStepAppearsLater}</p>
            )}
          </Card>
        </aside>
      </section>
    </PageShell>
  );
}
