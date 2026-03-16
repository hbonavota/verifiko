import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import {
  activityFeed,
  currentVerification,
  dashboardMetrics,
  decisionTrace,
  flagReasons,
} from "../data/mockDashboard";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";

function toneForActivity(type: string) {
  if (type === "signal_detected") {
    return "warning" as const;
  }

  if (type === "case_created") {
    return "danger" as const;
  }

  if (type === "analyst_comment") {
    return "primary" as const;
  }

  return "neutral" as const;
}

export function DashboardPage() {
  useDocumentMeta(
    "Verification Dashboard",
    "Analyst-facing operations dashboard for reviewing suspicious digital content, inspecting evidence, and deciding next actions in Verifiko.",
  );

  return (
    <PageShell>
      <SectionTitle
        eyebrow="Operations Overview"
        title="Verification Dashboard"
        description="Investigation workspace for reviewing suspicious digital content, inspecting evidence, and deciding next operational actions."
      />

      <Card
        eyebrow="Analysis intake"
        title="Start a new verification"
        description="Primary analyst entry point for suspicious URLs, domains, or text fragments requiring explainable review."
        tone="success"
        id="verifications"
        className="dashboard-intake-card"
      >
        <div className="dashboard-intake">
          <Input
            className="dashboard-intake__input-control"
            hint="URL, hostname, or suspicious text snippet."
            label="Analysis target"
            placeholder="Paste suspicious URL or content to analyze"
          />
          <Button variant="primary">Analyze now</Button>
        </div>
      </Card>

      <section className="dashboard-summary-grid">
        <Card
          eyebrow="Current assessment"
          title="Latest verification"
          description={currentVerification.summary}
          tone="warning"
          className="dashboard-assessment-card"
        >
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">Latest assessed target</p>
                <p className="dashboard-card__target">{currentVerification.subject}</p>
              </div>
              <Badge label={currentVerification.riskLevel} tone={toneForRiskLevel(currentVerification.riskLevel)} />
            </div>
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">Risk score</p>
                <p className="metric-card__value">{currentVerification.score}</p>
              </div>
              <div className="dashboard-card__run">
                <p className="metric-card__label">Verdict posture</p>
                <p className="dashboard-card__verdict">{currentVerification.verdict}</p>
              </div>
            </div>
            <div className="dashboard-card-headline dashboard-card-headline--muted">
              <div>
                <p className="metric-card__label">Verification run</p>
                <p className="dashboard-card__run-id">{currentVerification.id}</p>
              </div>
              <div className="dashboard-card__next-step">
                <p className="metric-card__label">Recommended next step</p>
                <p className="dashboard-card__next-step-text">
                  Escalate for infrastructure validation before containment.
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card
          eyebrow="Operational summary"
          title="Current workload"
          description="Queue and case counts for the active review window."
          className="dashboard-summary-card"
        >
          <div className="dashboard-card-pills dashboard-card-pills--stack">
            <StatPill label="Pending reviews" value={String(dashboardMetrics.pendingReviews)} />
            <StatPill label="Active cases" value={String(dashboardMetrics.activeCases)} tone="warning" />
            <StatPill label="High-risk queue" value={String(dashboardMetrics.highRiskQueue)} tone="danger" />
          </div>
        </Card>

        <Card
          eyebrow="System health"
          title="Backend and environment status"
          description="Compact operational strip for stack condition and recent execution context."
          className="dashboard-summary-card"
        >
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <Badge label={dashboardMetrics.apiStatus} tone="success" />
              <Badge label={dashboardMetrics.environmentLabel} tone="neutral" />
            </div>
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">Last verification run</p>
                <p className="metric-card__detail">
                  {new Date(dashboardMetrics.lastVerificationAt).toLocaleString()}
                </p>
              </div>
              <p className="metric-card__detail">
                {dashboardMetrics.flaggedSignals} flagged signals currently in scope
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
            title="Current verification signals"
            description="Inspection table for the signals currently shaping the score."
            id="signals"
          >
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
              {currentVerification.signals.map((signal) => (
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
          </Card>

          <section className="dashboard-inspection-grid">
            <Card
              eyebrow="Why this was flagged"
              title="Most influential signals"
              description="Readable reasoning for the observations that materially moved the verification into a suspicious range."
          >
            <div className="support-list">
                {flagReasons.map((reason, index) => (
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
              <div className="evidence-grid">
                <div className="evidence-block">
                  <p className="evidence-block__label">Observed</p>
                  <ul className="evidence-block__list">
                    {currentVerification.evidenceSummary.observed.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div className="evidence-block">
                  <p className="evidence-block__label">Sources</p>
                  <ul className="evidence-block__list">
                    {currentVerification.evidenceSummary.sources.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div className="evidence-block">
                  <p className="evidence-block__label">Unresolved</p>
                  <ul className="evidence-block__list">
                    {currentVerification.evidenceSummary.unresolved.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>
          </section>

          <Card
            eyebrow="Decision trace"
            title="Score generation sequence"
            description="Sequential reasoning chain from normalized input to explanation output."
            id="cases"
          >
            <div className="decision-trace">
              {decisionTrace.map((step) => (
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
          </Card>

          <Card
            eyebrow="Case recommendation"
            title="Suggested next action"
            description="Operational framing derived from the current evidence posture."
            tone="warning"
          >
            <div className="recommendation-panel">
              <p className="recommendation-panel__headline">
                Escalate for infrastructure validation before containment.
              </p>
              <p className="recommendation-panel__copy">
                The current evidence supports analyst escalation, but passive DNS and hosting context
                should be attached before a final block recommendation is issued.
              </p>
            </div>
          </Card>
        </div>

        <aside className="dashboard-rail">
          <Card
            eyebrow="Actions"
            title="Operational controls"
            description="Primary handling actions for the active verification."
            tone="warning"
            className="dashboard-rail-card dashboard-rail-card--primary"
          >
            <div className="action-stack">
              <Button variant="primary">Open raw evidence</Button>
              <Button variant="secondary">Assign case</Button>
              <Button variant="ghost">Export report</Button>
            </div>
          </Card>

          <Card
            eyebrow="Recent activity"
            title="Verification events"
            description="Chronological context for what changed during the current review flow."
            className="dashboard-rail-card"
          >
            <div className="activity-feed">
              {activityFeed.map((item) => (
                <article key={item.id} className="activity-feed__item">
                  <div className="activity-feed__row">
                    <p className="activity-feed__title">{item.title}</p>
                    <span className={`activity-feed__actor activity-feed__actor--${toneForActivity(item.type)}`}>
                      {item.actor}
                    </span>
                  </div>
                  <p className="activity-feed__detail">{item.detail}</p>
                  <p className="activity-feed__timestamp">{new Date(item.timestamp).toLocaleString()}</p>
                </article>
              ))}
            </div>
          </Card>

          <Card
            eyebrow="Analyst notes"
            title="Case annotations"
            description="Working note surface for the current analyst view."
            tone="warning"
            className="dashboard-rail-card"
          >
            <div className="notes-panel">
              <p className="notes-panel__text">{currentVerification.analystNote}</p>
              <p className="notes-panel__meta">
                Current posture: additional infrastructure context is needed before the verification
                can be closed with a hard action recommendation.
              </p>
            </div>
          </Card>

          <Card
            eyebrow="Context"
            title="Confidence posture"
            description="Small operational context card for unresolved evidence and review pressure."
            id="settings"
            className="dashboard-rail-card dashboard-rail-card--secondary"
          >
            <div className="dashboard-card-pills dashboard-card-pills--stack">
              <StatPill label="Confidence posture" value={dashboardMetrics.confidencePosture} tone="warning" />
              <StatPill
                label="Unresolved evidence"
                value={String(dashboardMetrics.unresolvedEvidenceCount)}
                tone="danger"
              />
              <StatPill label="Data mode" value="Typed mock data" />
            </div>
          </Card>
        </aside>
      </section>
    </PageShell>
  );
}
