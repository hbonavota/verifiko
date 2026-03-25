import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { createVerification, listVerifications } from "../lib/api";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";
import type { RiskLevel, VerificationSummary } from "../types/verification";

function toneForCount(riskLevel: RiskLevel) {
  return toneForRiskLevel(riskLevel);
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [analysisTarget, setAnalysisTarget] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);

  useDocumentMeta(
    "Verification Dashboard",
    "Analyst-facing operations dashboard for reviewing suspicious digital content, inspecting evidence, and deciding next actions in Verifiko.",
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
  const totalVerifications = verifications.length;
  const completedVerifications = verifications.filter(
    (verification) => verification.status === "COMPLETED",
  ).length;
  const higherRiskVerifications = verifications.filter(
    (verification) => verification.riskLevel === "HIGH" || verification.riskLevel === "CRITICAL",
  ).length;
  const mediumOrHigherVerifications = verifications.filter(
    (verification) =>
      verification.riskLevel === "MEDIUM" ||
      verification.riskLevel === "HIGH" ||
      verification.riskLevel === "CRITICAL",
  ).length;

  const activeReasons =
    activeVerification && activeVerification.signals.length > 0
      ? activeVerification.signals.slice(0, 3).map((signal) => signal.reason)
      : ["No verification record is currently available in this runtime."];

  async function handleAnalyze() {
    const trimmedTarget = analysisTarget.trim();
    if (!trimmedTarget) {
      setSubmitError("Enter a suspicious URL to analyze.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

      try {
        const verification = await createVerification({ url: trimmedTarget });
        navigate(`/verifications/${verification.id}`);
      } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Verification request failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <PageShell>
      <SectionTitle
        eyebrow="Operations Overview"
        title="Verification Dashboard"
        description="API-backed workspace for creating verifications, reviewing the current runtime records, and inspecting the latest result."
      />

      <Card
        eyebrow="Analysis intake"
        title="Start a new verification"
        description="Primary entry point for suspicious URLs or hostnames requiring explainable review."
        tone="success"
        id="verifications"
        className="dashboard-intake-card"
      >
        <div className="dashboard-intake">
          <Input
            className="dashboard-intake__input-control"
            hint="Suspicious URL or hostname."
            label="Analysis target"
            placeholder="Paste suspicious URL or hostname to analyze"
            value={analysisTarget}
            onChange={(event) => setAnalysisTarget(event.target.value)}
          />
          <Button variant="primary" onClick={() => void handleAnalyze()} disabled={isSubmitting}>
            {isSubmitting ? "Analyzing..." : "Analyze now"}
          </Button>
        </div>
        {submitError ? <p className="metric-card__detail">{submitError}</p> : null}
      </Card>

      <section className="dashboard-summary-grid">
        <Card
          eyebrow="Current assessment"
          title={activeVerification ? "Latest verification" : "No verifications in current runtime"}
          description={
            activeVerification
              ? activeVerification.summary
              : "Create a verification to populate the current backend runtime and begin reviewing live results."
          }
          tone="warning"
          className="dashboard-assessment-card"
        >
          {activeVerification ? (
            <div className="dashboard-card-stack">
              <div className="dashboard-card-headline">
                <div>
                  <p className="metric-card__label">Latest assessed target</p>
                  <p className="dashboard-card__target">{activeVerification.subject}</p>
                </div>
                <Badge label={activeVerification.riskLevel} tone={toneForRiskLevel(activeVerification.riskLevel)} />
              </div>

              <div className="dashboard-card-headline">
                <div>
                  <p className="metric-card__label">Risk score</p>
                  <p className="metric-card__value">{activeVerification.score}</p>
                </div>
                <div className="dashboard-card__run">
                  <p className="metric-card__label">Verdict posture</p>
                  <p className="dashboard-card__verdict">{activeVerification.verdict}</p>
                </div>
              </div>

              <div className="dashboard-card-headline dashboard-card-headline--muted">
                <div>
                  <p className="metric-card__label">Verification run</p>
                  <p className="dashboard-card__run-id">{activeVerification.id}</p>
                </div>
                <div className="dashboard-card__next-step">
                  <p className="metric-card__label">Recommended next step</p>
                  <p className="dashboard-card__next-step-text">{activeVerification.recommendation.title}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="dashboard-card-stack">
              <div className="dashboard-card-headline">
                <div>
                  <p className="metric-card__label">Runtime status</p>
                  <p className="dashboard-card__target">No verification records yet</p>
                </div>
                <Badge label="EMPTY" tone="neutral" />
              </div>
              <p className="metric-card__detail">
                The current backend runtime has not stored any verification records yet.
              </p>
            </div>
          )}
        </Card>

        <Card
          eyebrow="Runtime summary"
          title="Current in-memory records"
          description="Counts below are derived from the verifications currently available through the API list route."
          className="dashboard-summary-card"
        >
          <div className="dashboard-card-pills dashboard-card-pills--stack">
            <StatPill label="Stored records" value={String(totalVerifications)} />
            <StatPill label="Completed runs" value={String(completedVerifications)} tone="success" />
            <StatPill label="Medium or higher risk" value={String(mediumOrHigherVerifications)} tone="warning" />
          </div>
        </Card>

        <Card
          eyebrow="Current runtime"
          title="Session scope"
          description="This workspace reflects the current backend process only. Records disappear when the in-memory runtime restarts."
          className="dashboard-summary-card"
        >
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <Badge label="API-backed" tone="success" />
              <Badge label="In-memory storage" tone="neutral" />
            </div>
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">Latest runtime record</p>
                <p className="metric-card__detail">
                  {activeVerification ? new Date(activeVerification.createdAt).toLocaleString() : "No records yet"}
                </p>
              </div>
              <p className="metric-card__detail">
                {higherRiskVerifications} high-risk record{higherRiskVerifications === 1 ? "" : "s"} currently retained
              </p>
            </div>
            <div className="dashboard-card-pills">
              <Button to="/api-health" variant="ghost">
                View API health
              </Button>
            </div>
          </div>
        </Card>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <Card
            eyebrow="Signal breakdown"
            title={activeVerification ? "Current verification signals" : "Signal breakdown unavailable"}
            description={
              activeVerification
                ? "Inspection table for the signals currently shaping the score."
                : "Create a verification to inspect the retained signals shaping a live result."
            }
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
                No live verification is available yet for signal inspection.
              </p>
            )}
          </Card>

          <section className="dashboard-inspection-grid">
            <Card
              eyebrow="Why this was flagged"
              title="Most influential signals"
              description="Readable reasoning for the observations that materially moved the verification into a suspicious range."
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
              description="Traceability panel showing what supports the score and what still needs analyst judgment."
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
                  Evidence context will appear here once the current runtime contains a verification record.
                </p>
              )}
            </Card>
          </section>

          <Card
            eyebrow="Decision trace"
            title="Score generation sequence"
            description="Sequential reasoning chain from normalized input to explanation output."
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
                The current runtime has no verification record yet, so there is no trace sequence to display.
              </p>
            )}
          </Card>

          <Card
            eyebrow="Case recommendation"
            title="Suggested next action"
            description="Operational framing derived from the current evidence posture."
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
            eyebrow="Actions"
            title="Operational controls"
            description="Available navigation and review actions for the current runtime."
            tone="warning"
            className="dashboard-rail-card dashboard-rail-card--primary"
          >
            <div className="action-stack">
              {activeVerification ? (
                <Button to={`/verifications/${activeVerification.id}`} variant="primary">
                  Open live result
                </Button>
              ) : (
                <Button variant="primary" onClick={() => void handleAnalyze()} disabled={isSubmitting}>
                  Analyze target
                </Button>
              )}
              <Button to="/api-health" variant="secondary">
                Check API health
              </Button>
            </div>
          </Card>

          <Card
            eyebrow="Recent records"
            title="Latest verifications"
            description="Most recent verification records currently available from the API list route."
            className="dashboard-rail-card"
          >
            {verifications.length > 0 ? (
              <div className="activity-feed">
                {verifications.slice(0, 5).map((verification) => (
                  <article key={verification.id} className="activity-feed__item">
                    <div className="activity-feed__row">
                      <p className="activity-feed__title">{verification.subject}</p>
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
                No verification records are currently available in this backend runtime.
              </p>
            )}
          </Card>

          <Card
            eyebrow="Assessment note"
            title="Current result summary"
            description="Readable interpretation derived from the latest verification record rather than analyst-authored notes."
            tone="warning"
            className="dashboard-rail-card"
          >
            {activeVerification ? (
              <div className="notes-panel">
                <p className="notes-panel__text">{activeVerification.analystNote}</p>
                <p className="notes-panel__meta">{activeVerification.executiveSummary.operationalImpact}</p>
              </div>
            ) : (
              <p className="metric-card__detail">
                Summary notes appear here after the current runtime has a verification result.
              </p>
            )}
          </Card>

          <Card
            eyebrow="Runtime context"
            title="Current scope"
            description="Compact context card based on the current in-memory runtime instead of broader operational telemetry."
            id="settings"
            className="dashboard-rail-card dashboard-rail-card--secondary"
          >
            <div className="dashboard-card-pills dashboard-card-pills--stack">
              <StatPill label="Storage mode" value="In-memory runtime" />
              <StatPill
                label="Latest unresolved items"
                value={String(activeVerification?.inconclusive.length ?? 0)}
                tone="danger"
              />
              <StatPill label="API list records" value={String(totalVerifications)} />
            </div>
          </Card>
        </aside>
      </section>
    </PageShell>
  );
}
