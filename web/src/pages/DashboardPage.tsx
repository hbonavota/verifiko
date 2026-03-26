import { useEffect, useState } from "react";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { listVerifications } from "../lib/api";
import { formatVerdict } from "../lib/formatVerdict";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";
import type { RiskLevel, VerificationSummary } from "../types/verification";

function toneForCount(riskLevel: RiskLevel) {
  return toneForRiskLevel(riskLevel);
}

export function DashboardPage() {
  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);

  useDocumentMeta(
    "Review Results",
    "Review recent Verifiko analyses, inspect retained signals, and continue into detailed evidence.",
  );

  useEffect(() => {
    let isMounted = true;

    async function loadVerifications() {
      try {
        const payload = await listVerifications();
        if (!isMounted) {
          return;
        }

        setVerifications(payload.map(adaptApiVerification));
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
  }, []);

  const activeVerification = verifications[0] ?? null;

  const activeReasons =
    activeVerification && activeVerification.signals.length > 0
      ? activeVerification.signals.slice(0, 3).map((signal) => signal.reason)
      : ["No recent analysis is available yet."];

  return (
    <PageShell>
      <SectionTitle
        eyebrow="Review"
        title="Review results"
        description="Open a result or run another check."
      />

      <Card
        eyebrow="New analysis"
        title="Analyze another URL"
        description={undefined}
        tone="success"
        id="verifications"
        className="dashboard-intake-card"
      >
        <AnalyzeUrlForm
          buttonLabel="Analyze"
          className="dashboard-intake"
          hint="URL or hostname."
          inputClassName="dashboard-intake__input-control"
          inputLabel="URL"
          placeholder="Paste URL or hostname"
        />
      </Card>

      <Card
        eyebrow="Latest result"
        title={activeVerification ? "Trust score" : "No analyses yet"}
        description={undefined}
        tone="warning"
        className="dashboard-assessment-card"
      >
        {activeVerification ? (
          <div className="dashboard-card-stack">
            <div className="dashboard-assessment-card__hero">
              <ScoreRing
                label="Trust score"
                riskLevel={activeVerification.riskLevel}
                score={activeVerification.score}
                size="hero"
              />
              <div className="dashboard-assessment-card__summary">
                <p className="dashboard-card__subject" title={activeVerification.subject}>
                  {activeVerification.subject}
                </p>
                <div className="dashboard-card__status-row">
                  <Badge label={activeVerification.riskLevel} tone={toneForRiskLevel(activeVerification.riskLevel)} />
                </div>
                <p className="metric-card__label">Verdict</p>
                <p className="dashboard-card__verdict" title={activeVerification.verdict}>
                  {formatVerdict(activeVerification.verdict)}
                </p>
                <p className="dashboard-card__posture">{activeVerification.executiveSummary.posture}</p>
                <div className="dashboard-assessment-card__actions">
                  <Button to={`/verifications/${activeVerification.id}`} variant="primary">
                    Open result
                  </Button>
                </div>
              </div>
            </div>

            <div className="dashboard-card-headline dashboard-card-headline--muted">
              <div className="dashboard-card-pills">
                <StatPill label="Signals" value={String(activeVerification.signals.length)} tone="warning" />
                <StatPill label="Open questions" value={String(activeVerification.inconclusive.length)} tone="danger" />
              </div>
            </div>
          </div>
        ) : (
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">Status</p>
                <p className="dashboard-card__target">Ready for the first analysis</p>
              </div>
              <Badge label="EMPTY" tone="neutral" />
            </div>
          </div>
        )}
      </Card>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <Card
            eyebrow="Signal breakdown"
            title={activeVerification ? "Current verification signals" : "Signal breakdown unavailable"}
            description={undefined}
            id="signals"
          >
            {activeVerification ? (
              <div className="signal-table-wrap">
                <div className="signal-table">
                  <div className="signal-table__header">
                    <span>Signal name</span>
                    <span>Category</span>
                    <span>Severity</span>
                    <span>Confidence</span>
                    <span>Score contribution</span>
                    <span>Status</span>
                  </div>
                  {activeVerification.signals.map((signal) => (
                    <article key={signal.id} className="signal-table__row">
                      <div className="signal-table__identity">
                        <p className="signal-table__name">{signal.title}</p>
                        <p className="signal-table__subcopy">{signal.description}</p>
                      </div>
                      <span className="signal-table__value" data-label="Category">
                        {signal.category}
                      </span>
                      <div className="signal-table__cell" data-label="Severity">
                        <Badge label={signal.severity} tone={toneForRiskLevel(signal.severity)} />
                      </div>
                      <span className="signal-table__value" data-label="Confidence">
                        {signal.confidence}%
                      </span>
                      <span className="signal-table__value" data-label="Score contribution">
                        -{signal.scoreContribution}
                      </span>
                      <div className="signal-table__cell" data-label="Status">
                        <Badge label={signal.status} tone={toneForRiskLevel(signal.severity)} />
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <p className="metric-card__detail">
                No analysis is available yet for signal inspection.
              </p>
            )}
          </Card>

          <section className="dashboard-inspection-grid">
            <Card
              eyebrow="Why this was flagged"
              title="Most influential signals"
              description={undefined}
            >
              <div className="support-list">
                {activeReasons.map((reason, index) => (
                  <article key={reason} className="support-list__item support-list__item--plain">
                    <div>
                      <p className="support-list__title">Material factor {index + 1}</p>
                      <p className="support-list__description">{reason}</p>
                    </div>
                  </article>
                ))}
              </div>
            </Card>

            <Card
              eyebrow="Evidence snapshot"
              title="Observed, sourced, and unresolved context"
              description={undefined}
            >
              {activeVerification ? (
                <div className="evidence-grid">
                  <div className="evidence-block">
                    <p className="evidence-block__label">Observed</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.observed.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="evidence-block">
                    <p className="evidence-block__label">Sources</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.sources.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="evidence-block">
                    <p className="evidence-block__label">Unresolved</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.unresolved.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <p className="metric-card__detail">
                  Evidence context appears after the first analysis is available.
                </p>
              )}
            </Card>
          </section>

          <Card
            eyebrow="Decision trace"
            title="Score generation sequence"
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
              <p className="metric-card__detail">
                The decision trace will appear after the first result is available.
              </p>
            )}
          </Card>

          <Card
            eyebrow="Case recommendation"
            title="Suggested next action"
            description={undefined}
            tone="warning"
          >
            {activeVerification ? (
              <div className="recommendation-panel">
                <p className="recommendation-panel__headline">{activeVerification.recommendation.title}</p>
                <p className="recommendation-panel__copy">{activeVerification.recommendation.detail}</p>
              </div>
            ) : (
              <p className="metric-card__detail">
                Recommended action becomes available after a verification result is created.
              </p>
            )}
          </Card>
        </div>

        <aside className="dashboard-rail">
          <Card
            eyebrow="Recent analyses"
            title="Latest results"
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
                        {verification.riskLevel}
                      </span>
                    </div>
                    <p className="activity-feed__detail">{verification.summary}</p>
                    <p className="activity-feed__timestamp">
                      {new Date(verification.createdAt).toLocaleString()}
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="metric-card__detail">
                No results are available yet.
              </p>
            )}
          </Card>

          <Card
            eyebrow="Suggested next step"
            title="What to do next"
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
              <p className="metric-card__detail">
                A recommended next step appears after the first result is available.
              </p>
            )}
          </Card>
        </aside>
      </section>
    </PageShell>
  );
}
