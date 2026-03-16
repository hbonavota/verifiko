import { useParams } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { mockVerifications } from "../data/mockVerifications";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

export function VerificationDetailPage() {
  const { id } = useParams();
  const verification = mockVerifications.find((item) => item.id === id);

  const topSignals = verification
    ? [...verification.signals].sort((left, right) => right.scoreContribution - left.scoreContribution)
    : [];

  useDocumentMeta(
    verification ? `${verification.subject}` : "Verification Detail",
    verification
      ? `Evidence review for ${verification.subject}, including score rationale, signal materiality, unresolved items, and recommended action.`
      : "Verification detail route for reviewing score rationale, supporting evidence, and next-step guidance.",
  );

  if (!verification) {
    return (
      <PageShell>
        <SectionTitle
          eyebrow="Verification Detail"
          title="No matching verification was found in the current mock dataset."
          description="The requested verification is not present in the current demo dataset. Use the dashboard to return to the active review queue."
        />
        <Button to="/dashboard" variant="secondary">
          Return to dashboard
        </Button>
      </PageShell>
    );
  }

  const riskTone = toneForRiskLevel(verification.riskLevel);
  const emphasisTone =
    riskTone === "danger" ? "danger" : riskTone === "success" ? "success" : "warning";

  return (
    <PageShell>
      <section className="verification-detail-overview">
        <div className="verification-detail-overview__lead">
          <p className="eyebrow">Verification Detail</p>
          <h1 className="serif-heading verification-detail__title">{verification.subject}</h1>
          <p className="muted-copy verification-detail__summary-copy">
            Evidence review surface for score rationale, signal materiality, and operational next-step framing.
          </p>

          <div className="verification-detail-meta-grid">
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
        </div>

        <Card
          eyebrow="Assessment"
          title={verification.verdict}
          description={verification.summary}
          tone={emphasisTone}
          className="verification-assessment-card"
        >
          <div className="verification-assessment-card__topline">
            <Badge label={`${verification.riskLevel} RISK`} tone={toneForRiskLevel(verification.riskLevel)} />
            <p className="verification-assessment-card__status">{verification.status}</p>
          </div>

          <div className="verification-assessment-card__headline">
            <div>
              <p className="metric-card__label">Risk score</p>
              <p className="verification-assessment-card__score">{verification.score}</p>
            </div>
            <div className="verification-assessment-card__verdict-block">
              <p className="metric-card__label">Current posture</p>
              <p className="verification-assessment-card__verdict">{verification.executiveSummary.posture}</p>
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
            eyebrow="Executive summary"
            title="Current operational posture"
            description="Compact explanation of why this verification matters and how it should be interpreted."
          >
            <div className="verification-summary-panel">
              <p className="verification-summary-panel__headline">{verification.executiveSummary.posture}</p>
              <p className="verification-summary-panel__copy">
                {verification.executiveSummary.operationalImpact}
              </p>
            </div>
          </Card>

          <Card
            eyebrow="Top contributing signals"
            title="Signals shaping the current verdict"
            description="Highest scoring signals are shown first so material drivers are easy to inspect."
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
              <Badge label={verification.recommendation.priority} tone={toneForRiskLevel(verification.riskLevel)} />
              <p className="verification-action-card__copy">{verification.recommendation.detail}</p>
              <div className="verification-action-card__owner">
                <p className="verification-action-card__label">Suggested owner</p>
                <p className="verification-action-card__owner-value">{verification.recommendation.owner}</p>
              </div>
              <div className="action-stack">
                <Button to="/dashboard#cases" variant="primary">
                  Return to case queue
                </Button>
                <Button to="/dashboard#signals" variant="ghost">
                  Review signal workspace
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
